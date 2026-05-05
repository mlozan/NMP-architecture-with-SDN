clc; clear; close all;

VM_IP         = '192.168.1.193';  % ej: '192.168.1.50'
METRICS_URL   = sprintf('http://%s:9999/metrics', VM_IP);
QOE_THRESHOLD = 0.5;
POLL_INTERVAL = 4;       % segundos entre lecturas
COOLDOWN      = 15;      % segundos mínimos entre reroutings

% MACs — se imprimen al arrancar topo.py, actualiza aquí
SRC_MAC = '00:00:00:00:00:01';
DST_MAC = '00:00:00:00:00:02';

%% L_max (de tu análisis — valores fijos)
ED_M=[2.1407,2.1667,1.9067]; ED_CC=[1.3222,2.6542,2.2917];
ED_SH=[0.3778,0.5778,1.0267]; ED_D=[2.0148,4.3514,1.9067];
RC_M=[5.5337,5.5627,5.7094]; RC_CC=[3.4516,6.8903,5.6455];
RC_SH=[2.9364,5.3444,4.0208]; RC_D=[6.0285,5.7255,4.7548];

ED = mean([ED_M;ED_CC;ED_SH;ED_D],1);
RC = mean([RC_M;RC_CC;RC_SH;RC_D],1);
SE = [0.821, 0.884, 0.756];   % actualiza con tus valores MIR

SE_min=0.731; SE_max=0.936;
RC_min=min(RC); RC_max=max(RC);
L_base=40;

L_max = zeros(1,3);
for s=1:3
    L_max(s) = L_base ...
        * (1 - 0.4*max(0,min(1,(RC(s)-RC_min)/(RC_max-RC_min)))) ...
        * (1 - 0.35*max(0,min(1,(SE(s)-SE_min)/(SE_max-SE_min))));
end
song_names = {'Bolero','Master Blaster','Yellow Submarine'};
fprintf('L_max → Bolero:%.1fms  MB:%.1fms  YS:%.1fms\n\n', L_max);

%% Bucle
last_reroute = -Inf;
priority     = 100;
opts_get     = weboptions('Timeout',5);

fprintf('%-5s %-8s %-8s %-6s %-8s  QoE peor\n','Iter','Lat','Jit','Loss','D');
fprintf('%s\n', repmat('-',1,55));

for iter = 1:9999
    pause(POLL_INTERVAL);

    %% 1. Descargar CSV desde la VM
    try
        tmpfile = [tempdir 'metrics.csv'];
        websave(tmpfile, METRICS_URL, opts_get);
        data = readmatrix(tmpfile, 'NumHeaderLines', 1);
        if isempty(data), continue; end
    catch
        fprintf('[%03d] Sin datos todavía...\n', iter);
        continue
    end

    last       = data(end,:);
    latency_ms = last(2);
    jitter_ms  = last(3);
    loss_frac  = last(4) / 100;

    %% 2. Calcular D y QoE
    D = latency_ms + 1.5*jitter_ms + 500*loss_frac;

    worst_qoe  = Inf;
    worst_idx  = 1;
    for s=1:3
        q = max(0, 1 - D/L_max(s));
        if q < worst_qoe
            worst_qoe = q;
            worst_idx = s;
        end
    end

    fprintf('[%03d] %6.1fms %5.1fms %5.1f%% %6.1fms  %.3f (%s) %s\n', ...
        iter, latency_ms, jitter_ms, last(4), D, ...
        worst_qoe, song_names{worst_idx}, qoe_label(worst_qoe));

    %% 3. Rerouting si necesario
    now = posixtime(datetime('now'));
    if worst_qoe < QOE_THRESHOLD && (now - last_reroute) > COOLDOWN
        fprintf('\n>>> QoE=%.3f < %.1f — Rerouting via ONOS <<<\n\n', ...
                worst_qoe, QOE_THRESHOLD);
        priority     = priority + 10;
        ok           = onos_reroute(SRC_MAC, DST_MAC, priority);
        last_reroute = now;
    end
end

function lbl = qoe_label(q)
    if q>=0.8, lbl='Excellent';
    elseif q>=0.6, lbl='Good';
    elseif q>=0.4, lbl='Fair';
    elseif q>0,    lbl='Poor';
    else,          lbl='Unacceptable'; end
end