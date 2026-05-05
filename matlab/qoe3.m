% Open UDP socket on port 5006
u = udpport("datagram","IPV4","LocalPort",5006);
disp("Waiting for metrics...");

% Maximum degradation reference value for QoE normalization
L_base = 40;


% ONOS REST API base URL
onos_base = "http://192.168.56.101:8181/onos/v1";

% s1 device ID and port towards s2 (Path A)
s1_id   = "of:0000000000000001";
port_s2 = "2";  % s1-eth2 → s2 (Path A)

% Web options
options_get = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','get');

options_delete = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','delete');

% Track current state to avoid redundant calls
path_degraded = false;

while true
    if u.NumDatagramsAvailable > 0

        % Read one datagram as raw bytes
        datagram = read(u, 1, "uint8");
        rawBytes = datagram.Data;
        data     = strtrim(char(rawBytes));

        % Parse: "delay jitter loss"
        v = str2double(split(string(data)));
        if numel(v) < 3 || any(isnan(v))
            disp("Invalid packet");
            continue;
        end

        delay  = v(1);
        jitter = v(2);
        loss   = v(3);

        % Weighted degradation score
        D   = delay + 1*jitter + 200*loss;
        QoE = max(0, 1 - D/L_base);

        fprintf("Delay=%.3f ms | Jitter=%.3f ms | Loss=%.0f%% | QoE=%.3f\n", ...
                delay, jitter, loss*100, QoE);

        if QoE < 0.7 && ~path_degraded
            % QoE dropped → disable Path A, force Path B
            disp("LOW QoE → Disabling Path A (s1->s2), rerouting via s3...");

            cmd_disable = sprintf( ...
                'curl -s -u onos:rocks -X POST -H "Content-Type: application/json" -d "{\"enabled\":false}" http://192.168.56.101:8181/onos/v1/devices/%s/portstate/%s', ...
                s1_id, port_s2);
            system(cmd_disable);

            % Flush flows so ONOS recomputes via Path B
            try
                devices = webread(onos_base + "/devices", options_get);
                for i = 1:numel(devices.devices)
                    deviceId = devices.devices(i).id;
                    cmd_flush = sprintf( ...
                        'curl -s -u onos:rocks -X DELETE http://192.168.56.101:8181/onos/v1/flows/%s', ...
                        deviceId);
                    system(cmd_flush);
                    fprintf("Flows flushed for device: %s\n", deviceId);
                end
                disp("All flows flushed → ONOS recomputing via Path B...");
            catch e
                fprintf("ONOS call failed: %s\n", e.message);
            end

            path_degraded = true;

        elseif QoE >= 0.7 && path_degraded
            % QoE recovered → re-enable Path A
            disp("QoE recovered → Re-enabling Path A (s1->s2)...");

            cmd_enable = sprintf( ...
                'curl -s -u onos:rocks -X POST -H "Content-Type: application/json" -d "{\"enabled\":true}" http://192.168.56.101:8181/onos/v1/devices/%s/portstate/%s', ...
                s1_id, port_s2);
            system(cmd_enable);

            % Flush flows so ONOS recomputes freely
            try
                devices = webread(onos_base + "/devices", options_get);
                for i = 1:numel(devices.devices)
                    deviceId = devices.devices(i).id;
                    cmd_flush = sprintf( ...
                        'curl -s -u onos:rocks -X DELETE http://192.168.56.101:8181/onos/v1/flows/%s', ...
                        deviceId);
                    system(cmd_flush);
                    fprintf("Flows flushed for device: %s\n", deviceId);
                end
                disp("Path A restored → ONOS recomputing...");
            catch e
                fprintf("ONOS call failed: %s\n", e.message);
            end

            path_degraded = false;
        end

    end
end