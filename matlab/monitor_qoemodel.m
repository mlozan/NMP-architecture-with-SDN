%% QoE Monitor + ONOS Rerouting + Real-time Plots
clc; clear; close all;

%% =========================================================
%% CONFIGURATION
%% =========================================================

% --- Experiment mode ---
% false = Experiment 1 (baseline, no rerouting)
% true  = Experiment 2 (rerouting active)
REROUTING_ENABLED = false;

% --- Network ---
UDP_PORT      = 5006;
ONOS_BASE     = 'http://192.168.56.101:8181/onos/v1';
ONOS_USER     = 'onos';
ONOS_PASS     = 'rocks';

% --- Topology ---
% S1 port 3 faces Path A (s1 → s3, shortest path)
% Disabling this port forces ONOS to reroute via Path B (s1 → s2 → s5 → s4)
S1_ID       = 'of:0000000000000001';
PORT_PATH_A = '3';

% --- QoE ---
QOE_THRESHOLD = 0.6;
COOLDOWN_S    = 30;     % minimum seconds between rerouting actions

% --- Plot settings ---
PLOT_WINDOW = 60;       % seconds of history shown in the plots

% --- Data logging ---
% All measurements are saved to a .mat file at the end for thesis analysis
LOG_ENABLED = true;

%% =========================================================
%% SONG SELECTION
%% =========================================================
SONGS = {
    'Bolero',           5.5337, 0.821, 2.1407;
    'Master Blaster',   3.4516, 0.884, 1.3222;
    'Yellow Submarine', 5.7094, 0.756, 1.9067;
};
song_names = SONGS(:,1);

try
    idx = listdlg( ...
        'ListString',    song_names, ...
        'SelectionMode', 'single', ...
        'PromptString',  'Select song for QoE analysis:', ...
        'ListSize',      [260 120], ...
        'Name',          'QoE Monitor');
    if isempty(idx), error('Cancelled'); end
catch
    fprintf('Available songs:\n');
    for k = 1:numel(song_names)
        fprintf('  %d. %s\n', k, song_names{k});
    end
    idx = input('Select song number: ');
    if isempty(idx) || idx < 1 || idx > numel(song_names)
        error('Invalid selection. Aborting.');
    end
end

SONG_NAME = SONGS{idx, 1};
RC        = SONGS{idx, 2};
SE        = SONGS{idx, 3};
ED        = SONGS{idx, 4};

fprintf('\nSelected song: %s  (RC=%.3f, SE=%.3f, ED=%.3f)\n\n', ...
        SONG_NAME, RC, SE, ED);

%% =========================================================
%% L_max COMPUTATION
%% =========================================================
L_base = 40;
RC_MIN = 2.9364;  RC_MAX = 6.8903;
SE_MIN = 0.731;   SE_MAX = 0.936;

rc_norm = max(0, min(1, (RC - RC_MIN) / (RC_MAX - RC_MIN)));
se_norm = max(0, min(1, (SE - SE_MIN) / (SE_MAX - SE_MIN)));
L_max   = L_base * (1 - 0.40 * rc_norm) * (1 - 0.35 * se_norm);

if REROUTING_ENABLED
    exp_label = 'Experiment 2 — WITH rerouting';
else
    exp_label = 'Experiment 1 — WITHOUT rerouting (baseline)';
end

fprintf('============================================\n');
fprintf(' %s\n', exp_label);
fprintf(' Song: %s\n', SONG_NAME);
fprintf('============================================\n');
fprintf(' L_max:         %.2f ms\n', L_max);
fprintf(' RC=%.3f (norm=%.2f)  SE=%.3f (norm=%.2f)\n', RC, rc_norm, SE, se_norm);
fprintf(' QoE threshold: %.2f\n', QOE_THRESHOLD);
fprintf(' Rerouting:     %s\n', mat2str(REROUTING_ENABLED));
fprintf(' UDP port:      %d\n', UDP_PORT);
fprintf('============================================\n\n');

%% =========================================================
%% ONOS REST OPTIONS
%% =========================================================
opts_get = weboptions( ...
    'Username',      ONOS_USER, ...
    'Password',      ONOS_PASS, ...
    'MediaType',     'application/json', ...
    'RequestMethod', 'get', ...
    'Timeout',       5);

opts_post = weboptions( ...
    'Username',      ONOS_USER, ...
    'Password',      ONOS_PASS, ...
    'MediaType',     'application/json', ...
    'RequestMethod', 'post', ...
    'Timeout',       5);

%% =========================================================
%% DATA LOGGING SETUP
%% =========================================================
% Pre-allocate log arrays (grow dynamically, trimmed at save)
log_t        = [];   % time since start [s]
log_delay    = [];   % delay [ms]
log_jitter   = [];   % jitter [ms]
log_loss     = [];   % loss fraction [0-1]
log_D        = [];   % composite degradation D [ms]
log_qoe      = [];   % QoE [0-1]
log_path     = [];   % active path: 0=A, 1=B

%% =========================================================
%% FIGURE SETUP — 3 subplots
%% =========================================================
fig = figure('Name', sprintf('QoE Monitor — %s — %s', SONG_NAME, exp_label), ...
             'NumberTitle', 'off', ...
             'Position', [50 50 1100 750]);

% --- Subplot 1: QoE over time ---
ax1 = subplot(3,1,1);
h_qoe    = animatedline(ax1, 'Color', [0.13 0.55 0.13], 'LineWidth', 2);
h_thresh = yline(ax1, QOE_THRESHOLD, '--r', 'LineWidth', 1.5, ...
                 'Label', sprintf('Threshold (%.2f)', QOE_THRESHOLD));
ylim(ax1, [0 1.05]);
ylabel(ax1, 'QoE');
title(ax1, sprintf('%s  |  Song: %s  |  L_{max} = %.1f ms', ...
      exp_label, SONG_NAME, L_max));
grid(ax1, 'on');
legend(ax1, 'QoE', 'Threshold', 'Location', 'southwest');

% --- Subplot 2: Delay / Jitter / Loss ---
ax2 = subplot(3,1,2);
h_delay  = animatedline(ax2, 'Color', [0.00 0.45 0.74], ...
                        'LineWidth', 1.5, 'DisplayName', 'Delay (ms)');
h_jitter = animatedline(ax2, 'Color', [0.85 0.33 0.10], ...
                        'LineWidth', 1.5, 'DisplayName', 'Jitter (ms)');
h_loss   = animatedline(ax2, 'Color', [0.49 0.18 0.56], ...
                        'LineWidth', 1.5, 'DisplayName', 'Loss (%)');
ylabel(ax2, 'ms  /  %');
title(ax2, 'Network Metrics — Delay / Jitter / Loss');
grid(ax2, 'on');
legend(ax2, 'Location', 'northwest');

% --- Subplot 3: Port traffic (bytes received per switch) ---
ax3 = subplot(3,1,3);
h_port_bars = bar(ax3, zeros(1,4), 'FaceColor', 'flat');
h_port_bars.CData = [0.00 0.45 0.74;
                     0.47 0.67 0.19;
                     0.85 0.33 0.10;
                     0.49 0.18 0.56];
set(ax3, 'XTickLabel', {'s1','s2','s3','s4'});
ylabel(ax3, 'Bytes received');
title(ax3, 'Switch Port Traffic (total bytes received)');
grid(ax3, 'on');

% Rerouting event markers
reroute_times = [];

%% =========================================================
%% CONGESTION EVENT MARKER
%% =========================================================
% Mark the moment you start iperf manually so it appears on the plot.
% Call mark_congestion_start() from the MATLAB command window when
% you paste the iperf commands into the Mininet CLI.
% Example: >> mark_congestion_start()
congestion_marked = false;
congestion_time   = NaN;

%% =========================================================
%% MAIN LOOP
%% =========================================================
u = udpport('datagram', 'IPv4', 'LocalPort', UDP_PORT);
fprintf('Listening for UDP metrics on port %d...\n\n', UDP_PORT);
fprintf('TIP: When you start iperf in Mininet, run this in the MATLAB\n');
fprintf('     command window to mark the congestion start on the plot:\n');
fprintf('     >> mark_congestion_start()\n\n');

path_degraded = false;
last_reroute  = -Inf;
iter          = 0;
t_start       = posixtime(datetime('now'));

fprintf('%-5s  %-8s %-8s %-7s  %-8s  %-6s  %-13s  %s\n', ...
        'Iter', 'Lat(ms)', 'Jit(ms)', 'Loss(%)', 'D(ms)', ...
        'QoE', 'Quality', 'Path');
fprintf('%s\n', repmat('-', 1, 74));

while true
    %% --- Wait for UDP datagram ---
    if u.NumDatagramsAvailable == 0
        pause(0.1);
        continue;
    end

    datagram = read(u, 1, 'uint8');
    raw      = strtrim(char(datagram.Data));

    v = str2double(split(string(raw)));
    if numel(v) < 3 || any(isnan(v))
        fprintf('[WARN] Invalid packet: "%s"\n', raw);
        continue;
    end

    delay_ms  = v(1);
    jitter_ms = v(2);
    loss_frac = v(3);
    iter      = iter + 1;

    t_now = posixtime(datetime('now')) - t_start;

    %% --- Compute D and QoE ---
    D   = delay_ms + jitter_ms + 200 * loss_frac;
    QoE = max(0, 1 - D / L_max);

    active_path = 'A';
    if path_degraded, active_path = 'B'; end

    fprintf('[%04d]  %7.2f  %7.2f  %6.1f   %7.2f  %5.3f  %-13s  Path %s\n', ...
            iter, delay_ms, jitter_ms, loss_frac * 100, D, QoE, ...
            qoe_label(QoE), active_path);

    %% --- Log data ---
    if LOG_ENABLED
        log_t(end+1)      = t_now;       %#ok<AGROW>
        log_delay(end+1)  = delay_ms;    %#ok<AGROW>
        log_jitter(end+1) = jitter_ms;   %#ok<AGROW>
        log_loss(end+1)   = loss_frac;   %#ok<AGROW>
        log_D(end+1)      = D;           %#ok<AGROW>
        log_qoe(end+1)    = QoE;         %#ok<AGROW>
        log_path(end+1)   = double(path_degraded); %#ok<AGROW>
    end

    %% --- Update plots ---
    addpoints(h_qoe, t_now, QoE);
    xlim(ax1, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    addpoints(h_delay,  t_now, delay_ms);
    addpoints(h_jitter, t_now, jitter_ms);
    addpoints(h_loss,   t_now, loss_frac * 100);
    xlim(ax2, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    % Draw congestion marker (vertical line when iperf started)
    if ~congestion_marked && ~isnan(congestion_time)
        xc1 = xline(ax1, congestion_time, '-b', 'LineWidth', 1.5, ...
                    'Label', 'Congestion start');
        xc1.Annotation.LegendInformation.IconDisplayStyle = 'off';
        xc2 = xline(ax2, congestion_time, '-b', 'LineWidth', 1.5);
        xc2.Annotation.LegendInformation.IconDisplayStyle = 'off';
        congestion_marked = true;
        fprintf('\n[INFO] Congestion start marked at t=%.1fs\n\n', congestion_time);
    end

    % Subplot 3: port traffic from ONOS
    try
        stats = webread(sprintf('%s/statistics/ports', ONOS_BASE), opts_get);
        bytes_per_switch = zeros(1,4);
        dev_ids = {'of:0000000000000001', 'of:0000000000000002', ...
                   'of:0000000000000003', 'of:0000000000000004'};
        for d = 1:numel(stats)
            dev = stats(d);
            for dd = 1:4
                if strcmp(dev.device, dev_ids{dd})
                    total = 0;
                    for p = 1:numel(dev.statistics)
                        total = total + dev.statistics(p).bytesReceived;
                    end
                    bytes_per_switch(dd) = total;
                end
            end
        end
        h_port_bars.YData = bytes_per_switch;
    catch
        % Skip port stats if ONOS call fails
    end

    % Draw rerouting markers
    if ~isempty(reroute_times)
        xl1 = xline(ax1, reroute_times(end), '--k', 'Alpha', 0.4);
        xl1.Annotation.LegendInformation.IconDisplayStyle = 'off';
        xl2 = xline(ax2, reroute_times(end), '--k', 'Alpha', 0.4);
        xl2.Annotation.LegendInformation.IconDisplayStyle = 'off';
    end

    drawnow limitrate;

    %% --- Rerouting logic ---
    now_unix    = posixtime(datetime('now'));
    cooldown_ok = (now_unix - last_reroute) > COOLDOWN_S;

    if REROUTING_ENABLED
        if QoE < QOE_THRESHOLD && cooldown_ok
            if ~path_degraded
                fprintf('\n>>> QoE=%.3f < %.3f — Switching to Path B ', ...
                        QoE, QOE_THRESHOLD);
                fprintf('(disabling port %s on %s)...\n', PORT_PATH_A, S1_ID);

                ok = onos_set_port(ONOS_BASE, S1_ID, PORT_PATH_A, false, opts_post);
                if ok
                    flush_flows(ONOS_BASE, ONOS_USER, ONOS_PASS, opts_get);
                    path_degraded = true;
                    last_reroute  = now_unix;
                    reroute_times(end+1) = t_now; %#ok<AGROW>
                    fprintf('>>> Path B active. Flows flushed — ONOS recomputing...\n\n');
                else
                    fprintf('[ERROR] Could not disable port. Retrying next cycle.\n\n');
                end

            else
                fprintf('\n>>> QoE=%.3f still low on Path B — restoring Path A...\n', QoE);

                ok = onos_set_port(ONOS_BASE, S1_ID, PORT_PATH_A, true, opts_post);
                if ok
                    flush_flows(ONOS_BASE, ONOS_USER, ONOS_PASS, opts_get);
                    path_degraded = false;
                    last_reroute  = now_unix;
                    reroute_times(end+1) = t_now; %#ok<AGROW>
                    fprintf('>>> Path A restored. Flows flushed — ONOS recomputing...\n\n');
                else
                    fprintf('[ERROR] Could not re-enable port.\n\n');
                end
            end
        end
    end
end

%% =========================================================
%% SAVE RESULTS  (call this from command window to stop + save)
%% =========================================================
% When you want to stop the experiment, press Ctrl+C in MATLAB,
% then run this block manually in the command window:
%
%   save_experiment_results()
%
% Or just run these lines directly:
%
%   exp_num = 1;   % or 2
%   save(sprintf('exp%d_%s_%s.mat', exp_num, ...
%        strrep(SONG_NAME,' ','_'), datestr(now,'yyyymmdd_HHMMSS')), ...
%        'log_t','log_delay','log_jitter','log_loss','log_D','log_qoe', ...
%        'log_path','reroute_times','congestion_time', ...
%        'SONG_NAME','L_max','QOE_THRESHOLD','REROUTING_ENABLED');
%   fprintf('Results saved.\n');

%% =========================================================
%% HELPER FUNCTIONS
%% =========================================================

function mark_congestion_start()
% Call this from the MATLAB command window the moment you
% start iperf in Mininet. It marks the congestion start time
% on the plot with a blue vertical line.
    assignin('base', 'congestion_time', ...
             posixtime(datetime('now')) - evalin('base','t_start'));
    fprintf('[INFO] Congestion marker set.\n');
end

function ok = onos_set_port(base, device_id, port, enabled, opts)
    try
        url = sprintf('%s/devices/%s/portstate/%s', base, device_id, port);
        webwrite(url, struct('enabled', enabled), opts);
        ok = true;
    catch e
        fprintf('[ERROR] onos_set_port: %s\n', e.message);
        ok = false;
    end
end

function flush_flows(base, user, pass, ~)
% Delete flow rules only on s1 to force ONOS to recompute paths.
    try
        dev_id = 'of:0000000000000001';
        system(sprintf('curl -s -u %s:%s -X DELETE %s/flows/%s', ...
                       user, pass, base, dev_id));
        fprintf('   Flows deleted: %s\n', dev_id);
    catch e
        fprintf('[ERROR] flush_flows: %s\n', e.message);
    end
end

function lbl = qoe_label(q)
    if     q >= 0.8,  lbl = 'Excellent';
    elseif q >= 0.6,  lbl = 'Good';
    elseif q >= 0.4,  lbl = 'Fair';
    elseif q >  0,    lbl = 'Poor';
    else,             lbl = 'Unacceptable';
    end
end