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
ONOS_BASE     = 'http://192.168.56.102:8181/onos/v1';
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
log_path         = [];   % active path: 0=A, 1=B
log_phase_medium = [];   % t of medium congestion start (repeated per sample)
log_phase_heavy  = [];   % t of heavy congestion start (repeated per sample)

%% =========================================================
%% FIGURE SETUP — 3 subplots
%% =========================================================
% --- General figure title ---
fig_title = sprintf('Experiment 1 - No rerouting (baseline)  |  %s  |  L_{max} = %.1f ms', ...
                    SONG_NAME, L_max);

fig = figure('Name', fig_title, ...
             'NumberTitle', 'off', ...
             'Position', [50 50 1100 900]);

% Super title (general title for all subplots)
sgtitle(fig_title, 'FontSize', 13, 'FontWeight', 'bold');

% --- Subplot 1: QoE over time ---
ax1 = subplot(3,1,1);
h_qoe    = animatedline(ax1, 'Color', [0.13 0.55 0.13], 'LineWidth', 2);
h_thresh = yline(ax1, QOE_THRESHOLD, '--r', 'LineWidth', 1.5, ...
                 'Label', sprintf('Threshold (%.2f)', QOE_THRESHOLD));
ylim(ax1, [0 1.05]);
ylabel(ax1, 'QoE');
title(ax1, 'Quality of Experience');
grid(ax1, 'on');
legend(ax1, 'QoE', 'Threshold', 'Location', 'southwest');

% --- Subplot 2: Delay / Jitter ---
ax2 = subplot(3,1,2);
h_delay  = animatedline(ax2, 'Color', [0.00 0.45 0.74], ...
                        'LineWidth', 1.5, 'DisplayName', 'Delay (ms)');
h_jitter = animatedline(ax2, 'Color', [0.85 0.33 0.10], ...
                        'LineWidth', 1.5, 'DisplayName', 'Jitter (ms)');
ylabel(ax2, 'ms');
title(ax2, 'Network Metrics');
grid(ax2, 'on');
legend(ax2, 'Location', 'northwest');

% --- Subplot 3: Packet Loss ---
ax3 = subplot(3,1,3);
h_loss = animatedline(ax3, 'Color', [0.49 0.18 0.56], ...
                      'LineWidth', 1.5, 'DisplayName', 'Packet Loss (%)');
ylabel(ax3, '%');
xlabel(ax3, 'Time (s)');
title(ax3, 'Packet Loss');
grid(ax3, 'on');
legend(ax3, 'Location', 'northwest');



% Rerouting event markers
reroute_times = [];

%% =========================================================
%% PHASE SIGNAL — read automatically from /tmp/phase.txt
%% Written by experiment1_no_rerouting.py at each phase transition
%% Phases: 'none' | 'medium' | 'heavy'
%% =========================================================
PHASE_FILE      = '/tmp/phase.txt';
last_phase      = 'none';       % last phase read from file
phase_medium_t  = NaN;          % t when medium congestion started
phase_heavy_t   = NaN;          % t when heavy congestion started
phase_marked_medium = false;
phase_marked_heavy  = false;

%% =========================================================
%% MAIN LOOP
%% =========================================================
u = udpport('datagram', 'IPv4', 'LocalPort', UDP_PORT);
fprintf('Listening for UDP metrics on port %d...\n\n', UDP_PORT);
fprintf('Phase markers (no load / medium / heavy) are detected automatically\n');
fprintf('from /tmp/phase.txt written by experiment1_no_rerouting.py\n\n');

path_degraded = false;
last_reroute  = -Inf;
iter          = 0;
t_start       = posixtime(datetime('now'));

% --- Auto-save on exit (Ctrl+C, error, or normal stop) ---
% onCleanup runs this function no matter how the script stops.
clean = onCleanup(@() auto_save(fig, ax1, ax2, ax3, ...
    log_t, log_delay, log_jitter, log_loss, log_D, log_qoe, log_path, ...
    log_phase_medium, log_phase_heavy, phase_medium_t, phase_heavy_t, ...
    SONG_NAME, L_max, QOE_THRESHOLD, REROUTING_ENABLED));

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
        log_phase_medium(end+1) = phase_medium_t;  %#ok<AGROW>
        log_phase_heavy(end+1)  = phase_heavy_t;   %#ok<AGROW>
    end

    %% --- Update plots ---
    addpoints(h_qoe, t_now, QoE);
    xlim(ax1, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    addpoints(h_delay,  t_now, delay_ms);
    addpoints(h_jitter, t_now, jitter_ms);
    xlim(ax2, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    addpoints(h_loss, t_now, loss_frac * 100);
    xlim(ax3, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    %% --- Read phase signal file (written by experiment script) ---
    try
        current_phase = strtrim(fileread(PHASE_FILE));
    catch
        current_phase = 'none';
    end

    if ~strcmp(current_phase, last_phase)
        last_phase = current_phase;

        if strcmp(current_phase, 'medium') && ~phase_marked_medium
            phase_medium_t      = t_now;
            phase_marked_medium = true;
            col_m = [0.85 0.33 0.10];
            xline(ax1, phase_medium_t, '-', 'Color', col_m, 'LineWidth', 1.8, ...
                  'Label', 'Medium congestion', 'LabelVerticalAlignment', 'bottom');
            xline(ax2, phase_medium_t, '-', 'Color', col_m, 'LineWidth', 1.8);
            xline(ax3, phase_medium_t, '-', 'Color', col_m, 'LineWidth', 1.8);
            fprintf('\n[PHASE] Medium congestion started at t=%.1fs\n\n', phase_medium_t);

        elseif strcmp(current_phase, 'heavy') && ~phase_marked_heavy
            phase_heavy_t      = t_now;
            phase_marked_heavy = true;
            col_h = [0.64 0.08 0.18];
            xline(ax1, phase_heavy_t, '-', 'Color', col_h, 'LineWidth', 1.8, ...
                  'Label', 'Heavy congestion', 'LabelVerticalAlignment', 'bottom');
            xline(ax2, phase_heavy_t, '-', 'Color', col_h, 'LineWidth', 1.8);
            xline(ax3, phase_heavy_t, '-', 'Color', col_h, 'LineWidth', 1.8);
            fprintf('\n[PHASE] Heavy congestion started at t=%.1fs\n\n', phase_heavy_t);
        end
    end

    % Draw rerouting markers
    if ~isempty(reroute_times)
        xline(ax1, reroute_times(end), '--k', 'Alpha', 0.4, 'Label', 'Rerouting');
        xline(ax2, reroute_times(end), '--k', 'Alpha', 0.4);
        xline(ax3, reroute_times(end), '--k', 'Alpha', 0.4);
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

function auto_save(fig, ax1, ax2, ax3, ...
        log_t, log_delay, log_jitter, log_loss, log_D, log_qoe, log_path, ...
        log_phase_medium, log_phase_heavy, phase_medium_t, phase_heavy_t, ...
        SONG_NAME, L_max, QOE_THRESHOLD, REROUTING_ENABLED)
% Automatically called when the script stops (Ctrl+C, error, or normal end).
% Saves the figure as PNG and the workspace as .mat with the song name.

    fprintf('\n[AUTO-SAVE] Saving results for %s...\n', SONG_NAME);

    % Build safe filename (replace spaces with underscores)
    song_safe = strrep(SONG_NAME, ' ', '_');
    if REROUTING_ENABLED
        prefix = 'exp2';
    else
        prefix = 'exp1';
    end
    fname = sprintf('%s_%s', prefix, song_safe);

    % Fix x-axis to show full experiment from 0 to end
    if ~isempty(log_t)
        t_end = max(log_t);
        try
            xlim(ax1, [0, t_end]);
            xlim(ax2, [0, t_end]);
            xlim(ax3, [0, t_end]);
        catch
        end
    end

    % Export figure as PNG at 300 dpi
    try
        drawnow;
        exportgraphics(fig, sprintf('%s.png', fname), 'Resolution', 300);
        fprintf('[AUTO-SAVE] Figure saved: %s.png\n', fname);
    catch e
        fprintf('[AUTO-SAVE] Could not save figure: %s\n', e.message);
    end

    % Save workspace data as .mat
    try
        save(sprintf('%s.mat', fname), ...
             'log_t', 'log_delay', 'log_jitter', 'log_loss', ...
             'log_D', 'log_qoe', 'log_path', ...
             'log_phase_medium', 'log_phase_heavy', ...
             'phase_medium_t', 'phase_heavy_t', ...
             'SONG_NAME', 'L_max', 'QOE_THRESHOLD', 'REROUTING_ENABLED');
        fprintf('[AUTO-SAVE] Data saved:   %s.mat\n', fname);
    catch e
        fprintf('[AUTO-SAVE] Could not save .mat: %s\n', e.message);
    end

    % Save as Excel too
    try
        T = table(log_t', log_delay', log_jitter', log_loss' * 100, log_D', log_qoe', ...
                  'VariableNames', {'Time_s','Delay_ms','Jitter_ms','Loss_pct','D_ms','QoE'});
        writetable(T, sprintf('%s.xlsx', fname));
        fprintf('[AUTO-SAVE] Excel saved:  %s.xlsx\n', fname);
    catch e
        fprintf('[AUTO-SAVE] Could not save Excel: %s\n', e.message);
    end

    fprintf('[AUTO-SAVE] Done. Files saved in: %s\n', pwd);
end