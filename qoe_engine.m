clc; clear;

%% =========================
% 1. PAPER MODEL (KEEPED)
%% =========================

ED_M  = [2.1407, 2.1667, 1.9067];
ED_CC = [1.3222, 2.6542, 2.2917];
ED_SH = [0.3778, 0.5778, 1.0267];
ED_D  = [2.0148, 4.3514, 1.9067];

RC_M  = [5.5337, 5.5627, 5.7094];
RC_CC = [3.4516, 6.8903, 5.6455];
RC_SH = [2.9364, 5.3444, 4.0208];
RC_D  = [6.0285, 5.7255, 4.7548];

ED = mean([ED_M; ED_CC; ED_SH; ED_D], 1);
RC = mean([RC_M; RC_CC; RC_SH; RC_D], 1);

song_names = {'Bolero','MasterBlaster','YellowSubmarine'};

%% =========================
% 2. AUDIO FEATURES (OPTIONAL STATIC)
%% =========================

midi_files = {'Bolero-Ravel.mid','Master-Blaster.mid','Yellow-Submarine.mid'};
wav_files  = {'Bolero-Ravel.wav','Master-Blaster.wav','Yellow-Submarine.wav'};

BPM = zeros(1,3);
SE  = zeros(1,3);

for i = 1:3
    nmat = readmidi(midi_files{i});
    BPM(i) = gettempo(nmat);

    evalc('audio = miraudio(wav_files{i});');
    evalc('sp = mirspectrum(audio,''Frame'',0.05,0.5);');
    evalc('ent = mirentropy(sp);');
    vals = mirgetdata(ent);
    vals = vals(:);
    vals = vals(~isnan(vals) & vals > 0.1);
    SE(i) = mean(vals);
end

%% =========================
% 3. SELECT SINGLE SONG PROFILE
%% =========================

song_id = 1; % 👈 SOLO UNA CANCIÓN ACTIVA (Bolero)

RC_min = min(RC); RC_max = max(RC);
SE_min = 0.731; SE_max = 0.936;

RC_norm = (RC(song_id) - RC_min) / (RC_max - RC_min);
RC_norm = max(0,min(1,RC_norm));
F_rc = 1 - 0.4 * RC_norm;

SE_norm = (SE(song_id) - SE_min) / (SE_max - SE_min);
SE_norm = max(0,min(1,SE_norm));
F_se = 1 - 0.35 * SE_norm;

L_base = 40;
L_max = L_base * F_rc * F_se;

fprintf("\nL_max servicio (single song): %.2f ms\n\n", L_max);

%% =========================
% 4. UDP LISTENER (FROM MININET)
%% =========================

u = udpport("datagram","IPV4","LocalPort",5005);

fprintf("Esperando métricas de red...\n");

while true

    if u.NumDatagramsAvailable > 0

        data = read(u,1,"string");
        msg = jsondecode(data);

        latency = msg.latency;
        jitter  = msg.jitter;
        loss    = msg.loss;

        %% =========================
        % QoE MODEL (REAL-TIME)
        %% =========================

        D = latency + 1.5*jitter + 500*loss;

        QoE = max(0, 1 - D / L_max);

        fprintf("Latency=%.1f ms | QoE=%.3f\n", latency, QoE);

        %% =========================
        % SDN DECISION TRIGGER
        %% =========================

      if QoE < 0.4
    disp(">>> QoE LOW → trigger reroute ONOS");

    url = "http://192.168.1.193:8181/onos/v1/flows";

    options = weboptions( ...
        'Username','onos', ...
        'Password','rocks', ...
        'MediaType','application/json');

    % =========================
    % FLOW RULE (BASIC WORKING TEMPLATE)
    % =========================

    flow = struct();

    flow.priority = 40000;
    flow.timeout = 0;
    flow.isPermanent = true;

    % DEVICE WHERE RULE APPLIES (ej: s1)
    flow.deviceId = "of:0000000000000001";

    % =========================
    % MATCH (h1 → h2 traffic)
    % =========================

    flow.selector.criteria = { ...
        struct('type','ETH_TYPE','ethType','0x0800'), ...
        struct('type','IPV4_SRC','ip','10.0.0.1/32'), ...
        struct('type','IPV4_DST','ip','10.0.0.2/32') ...
    };

    % =========================
    % ACTION (FORWARD TO PATH 2)
    % =========================

    flow.treatment.instructions = { ...
        struct('type','OUTPUT','port','2') ...
    };

    % =========================
    % SEND TO ONOS
    % =========================

    webwrite(url, flow, options);
end