% Open UDP socket on port 5006
u = udpport("datagram","IPV4","LocalPort",5006);
disp("Waiting for metrics...");

% Maximum degradation reference value for QoE normalization
L_base = 40;

% ONOS REST API base URL and credentials
onos_base = "http://192.168.56.101:8181/onos/v1";

% s1 device ID and port towards s2 (Path A)
s1_id   = "of:0000000000000001";
port_s2 = "2";

% Options for GET requests to ONOS
options_get = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','get');

% Options for POST requests to ONOS
options_post = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','post');

% Track current path state
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
        D   = delay + jitter + 200*loss;
        QoE = max(0, 1 - D/L_base);

        fprintf("Delay=%.3f ms | Jitter=%.3f ms | Loss=%.0f%% | QoE=%.3f\n", ...
                delay, jitter, loss*100, QoE);

        % --- QoE degraded: disable Path A + flush flows ---
        if QoE < 0.4 && ~path_degraded
            disp("LOW QoE → Disabling Path A, forcing Path B...");

            try
                % Step 1: disable port s1 → s2 using webwrite
                url_port = sprintf('%s/devices/%s/portstate/%s', onos_base, s1_id, port_s2);
                webwrite(url_port, struct('enabled', false), options_post);
                disp("Port s1→s2 disabled");

                % Step 2: flush flows using curl (DELETE works fine)
                devices = webread(onos_base + "/devices", options_get);
                for i = 1:numel(devices.devices)
                    deviceId = devices.devices(i).id;
                    system(sprintf('curl -s -u onos:rocks -X DELETE %s/flows/%s', onos_base, deviceId));
                    fprintf("Flows flushed for device: %s\n", deviceId);
                end

                disp("Path A disabled + flows flushed → ONOS recomputing via Path B...");
            catch e
                fprintf("ONOS call failed: %s\n", e.message);
            end

            path_degraded = true;
            pause(2);

        % --- QoE recovered: re-enable Path A + flush flows ---
        elseif QoE >= 0.4 && path_degraded
            disp("QoE recovered → Re-enabling Path A...");

            try
                % Step 1: re-enable port s1 → s2 using webwrite
                url_port = sprintf('%s/devices/%s/portstate/%s', onos_base, s1_id, port_s2);
                webwrite(url_port, struct('enabled', true), options_post);
                disp("Port s1→s2 re-enabled");

                % Step 2: flush flows using curl (DELETE works fine)
                devices = webread(onos_base + "/devices", options_get);
                for i = 1:numel(devices.devices)
                    deviceId = devices.devices(i).id;
                    system(sprintf('curl -s -u onos:rocks -X DELETE %s/flows/%s', onos_base, deviceId));
                    fprintf("Flows flushed for device: %s\n", deviceId);
                end

                disp("Path A restored + flows flushed → ONOS recomputing...");
            catch e
                fprintf("ONOS call failed: %s\n", e.message);
            end

            path_degraded = false;
            pause(2);
        end

    end
end