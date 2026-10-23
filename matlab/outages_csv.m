function r=outages_csv(path)
% Preserve source row indices while converting timestamps to numeric hours.
t=readtable(path);if ismember('Duration',t.Properties.VariableNames),v=t.Duration;
else,v=hours(datetime(t.RestorationTime)-datetime(t.OutageTime));end
assert(~any(v<0),'Negative outage duration');r=outlier_detection(v);
end
