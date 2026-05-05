%% ===================================================================
%% QoE COMPARISON (3 MIDI) + JITTER + PACKET LOSS
%% ===================================================================

clear; close all; clc;

fprintf('=== QoE MODEL (Delay + Jitter + Packet Loss) ===\n\n');

%% ===================================================================
%% SELECT 3 MIDI FILES
%% ===================================================================

num_files = 3;

EDs = zeros(1, num_files);
RCs = zeros(1, num_files);
names = strings(1, num_files);

for k = 1:num_files
    fprintf('\nSelect MIDI file %d\n', k);
    
    [filename, pathname] = uigetfile('*.mid', 'Select a MIDI file');
    
    if filename == 0
        error('File selection cancelled');
    end
    
    midi_path = fullfile(pathname, filename);
    names(k) = filename;
    
    fprintf('Enter BPM for %s: ', filename);
    bpm = input('');
    
    [EDs(k), RCs(k)] = extract_features(midi_path, bpm);
    
    fprintf('→ ED = %.2f, RC = %.2f\n', EDs(k), RCs(k));
end

%% Mostrar resumen (clave para debug)
fprintf('\n=== FEATURE SUMMARY ===\n');
for k = 1:num_files
    fprintf('%s → ED=%.2f | RC=%.2f\n', names(k), EDs(k), RCs(k));
end

%% ===================================================================
%% NETWORK PARAMETERS
%% ===================================================================

fprintf('\nEnter network conditions:\n');

fprintf('Jitter (ms): ');
jitter = input('');

fprintf('Packet Loss (%%): ');
packet_loss = input('');

%% ===================================================================
%% SELECT INSTRUMENT
%% ===================================================================

fprintf('\nSelect instrument:\n');
fprintf('  1. Clarinet\n');
fprintf('  2. Piano\n');
fprintf('  3. Guitar\n');
fprintf('  4. Drums\n');

inst_choice = input('Choice (1-4): ');
SE_values = [0.731, 0.734, 0.841, 0.936];
SE = SE_values(inst_choice);

%% ===================================================================
%% COMPUTE QoE vs DELAY
%% ===================================================================

delays = 0:2:150;  % más suave tipo paper

QoE_all = zeros(num_files, length(delays));

for k = 1:num_files
    for i = 1:length(delays)
        QoE_all(k, i) = calculate_QoE( ...
            delays(i), EDs(k), RCs(k), SE, jitter, packet_loss);
    end
end

%% ===================================================================
%% DEFINE DSI (simple métrica agregada)
%% ===================================================================

DSI = mean(EDs .* RCs);

%% ===================================================================
%% PLOT ESTILO PAPER
%% ===================================================================

figure('Position', [100, 100, 900, 500]);

colors = [0 0.4470 0.7410;
          0.8500 0.3250 0.0980;
          0.4660 0.6740 0.1880];

for k = 1:num_files
    plot(delays, QoE_all(k, :), ...
        'LineWidth', 2.5, ...
        'Color', colors(k,:), ...
        'DisplayName', names(k));
    hold on;
end

% Líneas QoE
yline(4, '--', 'Good', 'LineWidth', 1);
yline(3, '--', 'Fair', 'LineWidth', 1);
yline(2, '--', 'Poor', 'LineWidth', 1);

xlabel('Latencia (ms)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('QoE (1-5)', 'FontSize', 12, 'FontWeight', 'bold');

title(sprintf('Degradación de QoE - DSI = %.3f', DSI), ...
    'FontSize', 14, 'FontWeight', 'bold');

grid on;
ylim([0 5.5]);
xlim([0 150]);

legend('Location', 'southwest');

set(gca, 'FontSize', 11);
box on;

fprintf('\n✓ Gráfica generada correctamente\n');

%% ===================================================================
%% FUNCTIONS
%% ===================================================================

function QoE = calculate_QoE(delay, ED, RC, SE, jitter, packet_loss)

    % -------- BASE DELAY SCORE --------
    if delay <= 25
        base_score = 5.0;
    elseif delay <= 40
        base_score = 4.0;
    elseif delay <= 60
        base_score = 3.0;
    elseif delay <= 80
        base_score = 2.5;
    else
        base_score = 2.0;
    end

    % -------- MUSIC PENALTIES --------
    RC_penalty = (RC / 6.5) * (delay / 100);
    ED_penalty = (ED / 3.0) * (delay / 120);
    SE_penalty = SE * (delay / 150);

    % -------- NETWORK PENALTIES --------
    jitter_penalty = 0.2 * (jitter / 10);
    loss_penalty = 0.3 * packet_loss;

    % -------- FINAL QoE --------
    QoE = base_score ...
        - 0.7*RC_penalty ...
        - 0.7*ED_penalty ...
        - 0.7*SE_penalty ...
        - jitter_penalty ...
        - loss_penalty;

    QoE = max(1, min(5, QoE));
end

function [ED, RC] = extract_features(midi_file, bpm)

    nmat = readmidi(midi_file);
    
    onsets_sec = onset(nmat, 'sec');
    duration_sec = max(onsets_sec);
    onsets_rounded = round(onsets_sec, 2);
    unique_onsets = unique(onsets_rounded);
    num_onsets = length(unique_onsets);
    ED = num_onsets / duration_sec;
    
    durations_sec = dur(nmat, 'sec');
    [counts, ~] = histcounts(durations_sec, 20);
    probs = counts / sum(counts);
    probs = probs(probs > 0);
    H = -sum(probs .* log2(probs));
    sigma = std(durations_sec);
    
    onsets_beats = onset(nmat, 'beats');
    beat_positions = mod(onsets_beats, 4);
    th = 0.15;
    
    on_strong = sum(beat_positions < th | abs(beat_positions - 2) < th);
    on_weak = sum(abs(beat_positions - 1) < th | abs(beat_positions - 3) < th);
    
    A = abs(on_strong - on_weak) / (on_strong + on_weak + 1);
    
    w1 = 0.7; w2 = 0.2; w3 = 0.5; w4 = 0.5;
    RC = w1*H + w2*ED + w3*sigma + w4*A;
end