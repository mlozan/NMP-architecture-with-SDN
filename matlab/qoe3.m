% Open UDP socket on port 5006
u = udpport("datagram","IPV4","LocalPort",5006);
disp("Waiting for metrics...");

% Maximum degradation reference value for QoE normalization
L_base = 40;

% ONOS REST API base URL
onos_base = "http://192.168.56.101:8181/onos/v1";

% s1 device ID and port towards s2 (Path A)
s1_id   = "of:0000000000000001";
port_s2 = "2";

% Web options for GET requests
options_get = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','get');

% Track current path state
path_degraded = false;

while true
    if u.NumDatagramsAvailable > 0

        % Read and parse UDP packet: "delay jitter loss"
        datagram = read(u, 1, "uint8");
        data = strtrim(char(datagram.Data));
        v = str2double(split(string(data)));

        if numel(v) < 3 || any(isnan(v))
            disp("Invalid packet");
            continue;
        end

        delay  = v(1);
        jitter = v(2);
        loss   = v(3);

        % Calculate QoE (0=bad, 1=perfect)
        D   = delay + jitter + 200*loss;
        QoE = max(0, 1 - D/L_base);

        fprintf("Delay=%.3f ms | Jitter=%.3f ms | Loss=%.0f%% | QoE=%.3f\n", ...
                delay, jitter, loss*100, QoE);

        % --- QoE degraded: disable Path A, ONOS will use Path B ---
        if QoE < 0.7 && ~path_degraded
            disp("LOW QoE → Disabling Path A, rerouting via Path B...");

            % Disable port s1 → s2
            system(sprintf( ...
                'curl -s -u onos:rocks -X POST -H "Content-Type: application/json" -d "{\\"enabled\\":\\"false\\"}" %s/devices/%s/portstate/%s', ...
                onos_base, s1_id, port_s2));

            path_degraded = true;
            disp("Path A disabled → ONOS now routes via Path B");

        % --- QoE recovered: re-enable Path A ---
        elseif QoE >= 0.7 && path_degraded
            disp("QoE recovered → Re-enabling Path A...");

            % Re-enable port s1 → s2
            system(sprintf( ...
                'curl -s -u onos:rocks -X POST -H "Content-Type: application/json" -d "{\\"enabled\\":\\"true\\"}" %s/devices/%s/portstate/%s', ...
                onos_base, s1_id, port_s2));

            path_degraded = false;
            disp("Path A restored → ONOS can use both paths again");
        end

    end
end