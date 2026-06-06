%% QoE Monitor + ONOS Rerouting + Real-time Plots
clc; clear; close all;

%% =========================================================
%% CONFIGURATION
%% =========================================================

% --- Experiment mode ---
% false = Experiment 1 (baseline, no rerouting)
% true  = Experiment 2 (rerouting active)
REROUTING_ENABLED = true;

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
% Musical parameters extracted from Rottondi et al. (2015), Tables 1 and 3.
%
% RC (Rhythmic Complexity): mean across all four roles (M, CC, SH, D)
%    from Table 1 of Rottondi et al.
%
% SE (Spectral Entropy): mean across selected instrument pair per song,
%    from Table 3 of Rottondi et al.
%    - Bolero:           Acoustic Guitar (SE=0.760) + Clarinet (SE=0.731)
%    - Master Blaster:   Electric Guitar (SE=0.818) + Drums (SE=0.936)
%    - Yellow Submarine: Electric Piano  (SE=0.734) + Drums (SE=0.936)
%
% ED (Event Density): mean across all four roles (M, CC, SH, D)
%    from Table 1 of Rottondi et al.
%    ED is not used directly in L_max (it is implicitly captured by RC),
%    but is logged for reference.
%
% Song parameters:       RC      SE      ED
SONGS = {
    'Bolero',           4.488,  0.746,  1.464;
    'Master Blaster',   5.881,  0.877,  2.438;
    'Yellow Submarine', 5.033,  0.835,  1.783;
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
% L_base: baseline latency tolerance (40ms), justified by Tsioutas et al.
%
% RC and SE are normalised to [0,1] using the min/max values observed
% across all roles and instruments in Rottondi et al. (2015):
%   RC_MIN = 2.9364 (Bolero, SH)    RC_MAX = 6.8903 (Master Blaster, CC)
%   SE_MIN = 0.731  (Clarinet)      SE_MAX = 0.936  (Drums)
%
<<<<<<< HEAD
% L_max pe
=======
% L_max pe
>>>>>>> 2de79cd632651a90c0402fe84db9baa8a1feaec8
