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
S1_ID       = 'of:0000000000000001';
PORT_PATH_A = '2';

% --- QoE ---
QOE_THRESHOLD = 0.6;
COOLDOWN_S    = 10;

% --- Plot window ---
PLOT_WINDOW = 60;

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
    exp_label = 'Experiment 2 - WITH rerouting';
else
    exp_label = 'Experiment 1 - No rerouting (baseline)';
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
%% FIGURE SETUP — 3 subplots
%% =========================================================
fig_title = sprintf('%s  |  %s  |  L_{max} = %.1f ms', ...
                    exp_label, SONG_NAME, L_max);

fig = figure('Name', fig_title, ...
             'NumberTitle', 'off', ...
             'Position', [50 50 1100 900]);

sgtitle(fig_title, 'FontSize', 13, 'FontWeight', 'bold');

% --- Subplot 1: QoE ---
ax1 = subplot(3,1,1);
h_qoe = animatedline(ax1, 'Color', [0.13 0.55 0.13], 'LineWidth', 2, 'DisplayName', 'QoE');
yline(ax1, QOE_THRESHOLD, '--r', 'LineWidth', 1.5, ...
      'Label', sprintf('Threshold (%.2f)', QOE_THRESHOLD), 'DisplayName', 'Threshold');
% Invisible line for rerouting legend entry — created after h_qoe and yline
line(ax1, NaN, NaN, 'LineStyle', '--', 'Color', 'k', 'LineWidth', 1.2, ...
     'DisplayName', 'Rerouting event');
ylim(ax1, [0 1.05]);
ylabel(ax1, 'QoE');
title(ax1, 'Quality of Experience');
grid(ax1, 'on');
legend(ax1, 'Location', 'southwest');

% --- Subplot 2: Delay / Jitter ---
ax2 = subplot(3,1,2);
h_delay  = animatedline(ax2, 'Color', [0.00 0.45 0.74], ...
                        'LineWidth', 1.5, 'DisplayName', 'Delay (ms)');
h_jitter = animatedline(ax2, 'Color', [0.85 0.33 0.10], ...
                        'LineWidth', 1.5, 'DisplayName', 'Jitter (ms)');
ylabel(ax2, 'ms');
title(ax2, 'Network Metrics');
grid(ax2, 'on');
% Invisible line for rerouting legend entry on ax2
h_reroute_leg2 = line(ax2, NaN, NaN, 'LineStyle', '--', 'Color', 'k', 'LineWidth', 1.2, 'DisplayName', 'Rerouting event');
legend(ax2, 'Location', 'northwest');

% --- Subplot 3: Packet Loss ---
ax3 = subplot(3,1,3);
h_loss = animatedline(ax3, 'Color', [0.49 0.18 0.56], ...
                      'LineWidth', 1.5, 'DisplayName', 'Packet Loss (%)');
ylabel(ax3, '%');
xlabel(ax3, 'Time (s)');
title(ax3, 'Packet Loss');
grid(ax3, 'on');
% Invisible line for rerouting legend entry on ax3
h_reroute_leg3 = line(ax3, NaN, NaN, 'LineStyle', '--', 'Color', 'k', 'LineWidth', 1.2, 'DisplayName', 'Rerouting event');
legend(ax3, 'Location', 'northwest');

reroute_times = [];

%% =========================================================
%% DATA LOG ARRAYS
%% =========================================================
log_t      = [];
log_delay  = [];
log_jitter = [];
log_loss   = [];
log_D      = [];
log_qoe    = [];

%% =========================================================
%% MAIN LOOP
%% =========================================================
u = udpport('datagram', 'IPv4', 'LocalPort', UDP_PORT);
fprintf('Listening for UDP metrics on port %d...\n\n', UDP_PORT);

path_degraded = false;
last_reroute  = -Inf;
iter          = 0;
t_start       = posixtime(datetime('now'));

fprintf('%-5s  %-8s %-8s %-7s  %-8s  %-6s  %-13s  %s\n', ...
        'Iter', 'Lat(ms)', 'Jit(ms)', 'Loss(%)', 'D(ms)', ...
        'QoE', 'Quality', 'Path');
fprintf('%s\n', repmat('-', 1, 74));

while true
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
    log_t(end+1)      = t_now;
    log_delay(end+1)  = delay_ms;
    log_jitter(end+1) = jitter_ms;
    log_loss(end+1)   = loss_frac;
    log_D(end+1)      = D;
    log_qoe(end+1)    = QoE;

    %% --- Update plots ---
    addpoints(h_qoe, t_now, QoE);
    xlim(ax1, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    addpoints(h_delay,  t_now, delay_ms);
    addpoints(h_jitter, t_now, jitter_ms);
    xlim(ax2, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);

    addpoints(h_loss, t_now, loss_frac * 100);
    xlim(ax3, [max(0, t_now - PLOT_WINDOW), max(PLOT_WINDOW, t_now)]);
    % Dynamic y-axis: always show at least 0-10%, scale up if needed
    if ~isempty(log_loss)
        max_loss = max(log_loss) * 100;
        ylim(ax3, [0, max(10, max_loss * 1.3)]);
    end

    %% --- Draw rerouting markers ---
    if ~isempty(reroute_times)
        xline(ax1, reroute_times(end), '--k', 'LineWidth', 1.2, ...
              'HandleVisibility', 'off');
        xline(ax2, reroute_times(end), '--k', 'LineWidth', 1.2, ...
              'HandleVisibility', 'off');
        xline(ax3, reroute_times(end), '--k', 'LineWidth', 1.2, ...
              'HandleVisibility', 'off');
    end

    drawnow limitrate;

    %% --- Rerouting logic ---
    now_unix    = posixtime(datetime('now'));
    cooldown_ok = (now_unix - last_reroute) > COOLDOWN_S;

    if REROUTING_ENABLED
        if QoE < QOE_THRESHOLD && cooldown_ok
            if ~path_degraded
                fprintf('\n>>> QoE=%.3f < %.3f — Switching to Path B...\n', ...
                        QoE, QOE_THRESHOLD);
                ok = onos_set_port(ONOS_BASE, S1_ID, PORT_PATH_A, false, opts_post);
                if ok
                    flush_flows(ONOS_BASE, ONOS_USER, ONOS_PASS);
                    path_degraded = true;
                    last_reroute  = now_unix;
                    reroute_times(end+1) = t_now; %#ok<AGROW>
                    fprintf('>>> Path B active. Flows flushed — ONOS recomputing...\n\n');
                else
                    fprintf('[ERROR] Could not disable port.\n\n');
                end
            else
                fprintf('\n>>> QoE=%.3f still low — restoring Path A...\n', QoE);
                ok = onos_set_port(ONOS_BASE, S1_ID, PORT_PATH_A, true, opts_post);
                if ok
                    flush_flows(ONOS_BASE, ONOS_USER, ONOS_PASS);
                    path_degraded = false;
                    last_reroute  = now_unix;
                    reroute_times(end+1) = t_now; %#ok<AGROW>
                    fprintf('>>> Path A restored.\n\n');
                else
                    fprintf('[ERROR] Could not re-enable port.\n\n');
                end
            end
        end
    end
end

%% =========================================================
%% ANALYSIS — paste in command window after Ctrl+C
%% =========================================================
%
% Fix axes and export figure:
%   song_safe = strrep(SONG_NAME, ' ', '_');
%   xlim(ax1,[0,max(log_t)]); xlim(ax2,[0,max(log_t)]); xlim(ax3,[0,max(log_t)]);
%   exportgraphics(fig, sprintf('exp1_%s.png', song_safe), 'Resolution', 300);
%
% Export to Excel:
%   T = table(log_t', log_delay', log_jitter', log_loss'*100, log_D', log_qoe', ...
%       'VariableNames', {'Time_s','Delay_ms','Jitter_ms','Loss_pct','D_ms','QoE'});
%   writetable(T, sprintf('exp1_%s.xlsx', song_safe));
%
% Print phase stats (adjust boundaries to match your experiment):
%   t1 = log_t < 60; t2 = log_t >= 60 & log_t < 120; t3 = log_t >= 120;
%   phases = {t1, t2, t3};
%   names  = {'Baseline (0-60s)', 'Medium (60-120s)', 'Heavy (120-180s)'};
%   for i = 1:3
%       p = phases{i};
%       fprintf('\n--- %s ---\n', names{i});
%       fprintf('  QoE mean:    %.3f\n',  mean(log_qoe(p)));
%       fprintf('  QoE min:     %.3f\n',  min(log_qoe(p)));
%       fprintf('  Delay mean:  %.2f ms\n', mean(log_delay(p)));
%       fprintf('  Jitter mean: %.2f ms\n', mean(log_jitter(p)));
%       fprintf('  Loss mean:   %.1f %%\n', mean(log_loss(p)*100));
%   end

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

function flush_flows(base, user, pass)
    try
        dev_id = 'of:0000000000000001';
        system(sprintf('curl -s -u %s:%s -X DELETE %s/flows/%s', ...
                       user, pass, base, dev_id));
        fprintf('   Flows deleted on s1.\n');
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