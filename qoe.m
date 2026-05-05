u = udpport("datagram","IPV4","LocalPort",5006);
disp("Waiting for metrics...");
L_base = 40;

while true
    if u.NumDatagramsAvailable > 0
        % ✔ Correct Datagram object reading
        datagram = read(u, 1, "uint8");          % read as raw bytes
        rawBytes = datagram.Data;                 % extract .Data field
        data     = strtrim(char(rawBytes));        % convert bytes → char → clean string

        v = str2double(split(string(data)));

        if numel(v) < 3 || any(isnan(v))
            disp("Invalid packet");
            continue;
        end

        delay  = v(1);
        jitter = v(2);
        loss   = v(3);

        D   = delay + 1*jitter + 200*loss;
        QoE = max(0, 1 - D/L_base);

        fprintf("Delay=%.6f | Jitter=%.6f | Loss=%.2f | QoE=%.3f\n", ...
                delay, jitter, loss, QoE);

        if QoE < 0.4
            disp("LOW QoE → REROUTE");
            url = "http://192.168.56.101:8181/onos/v1/intents";
            options = weboptions( ...
                'Username','onos', ...
                'Password','rocks', ...
                'MediaType','application/json');
            disp("Ready for ONOS");
        end
    end
end