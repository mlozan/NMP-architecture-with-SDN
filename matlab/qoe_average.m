% Open UDP socket on port 5006
u = udpport("datagram","IPV4","LocalPort",5006);
disp("Waiting for metrics...");

% Maximum degradation reference value for QoE normalization
L_base = 40;

% ONOS REST API base URL and credentials
onos_base = "http://192.168.56.101:8181/onos/v1";

% Options for GET requests to ONOS
options_get = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','get');

% Options for DELETE requests to ONOS
options_delete = weboptions( ...
    'Username','onos', ...
    'Password','rocks', ...
    'MediaType','application/json', ...
    'RequestMethod','delete');

while true
    if u.NumDatagramsAvailable > 0

        % Read one datagram as raw bytes
        datagram = read(u, 1, "uint8");

        % Extract the byte array from the Datagram object
        rawBytes = datagram.Data;

        % Convert bytes to a clean text string
        data = strtrim(char(rawBytes));

        % Split string by spaces and convert each value to double
        % Expected format: "delay jitter loss" e.g. "12.3 1.2 0.30"
        v = str2double(split(string(data)));

        % Discard packet if it does not contain exactly 3 valid numbers
        if numel(v) < 3 || any(isnan(v))
            disp("Invalid packet");
            continue;
        end

        delay  = v(1);   % Average RTT in milliseconds
        jitter = v(2);   % Real jitter (avg variation between consecutive RTTs)
        loss   = v(3);   % Packet loss ratio: 0.0 (none) to 1.0 (all lost)

        % Weighted degradation score D
        % - delay:  direct contribution in ms
        % - jitter: weighted x1.0 (buffer compesates jitter but introduces delay)
        % - loss:   weighted x200 
      
        D = delay + 1*jitter + 200*loss;

        % Normalize to QoE index between 0 (bad) and 1 (perfect)
        QoE = max(0, 1 - D/L_base);

        fprintf("Delay=%.3f ms | Jitter=%.3f ms | Loss=%.0f%% | QoE=%.3f\n", ...
                delay, jitter, loss*100, QoE);

        % If QoE drops below 0.4, network quality is unacceptable
        if QoE < 0.998
            disp("LOW QoE → REROUTE");
             try
        % Get devices via webread 
        devices = webread(onos_base + "/devices", options_get);

        for i = 1:numel(devices.devices)
            deviceId = devices.devices(i).id;
            cmd = sprintf('curl -s -u onos:rocks -X DELETE http://192.168.56.101:8181/onos/v1/flows/%s', deviceId);
            system(cmd);
            fprintf("Flows flushed for device: %s\n", deviceId);
        end

        disp("All flows flushed → ONOS recomputing paths...");

    catch e
        fprintf("ONOS call failed: %s\n", e.message);
    end
        end
    end
end