
cruiseplan process -c config/stations/msm142_cruise_v2.yaml --bathy-dir ../cruiseplan/data/bathymetry --bathy-source gebco2025 --bathy-stride 1 --output-dir schedule/ --no-ports --bathy-contour 700 800 900 1000


cruiseplan schedule -c schedule/MSM142_StJohns_enriched.yaml --bathy-dir ../cruiseplan/data/bathymetry --bathy-source gebco2025 -o schedule/ --format all  --lat 64 67 --lon -32 -26

cruiseplan stationplan --schedule schedule/MSM142_StJohns_schedule.nc --list

#cruiseplan stationplan --schedule schedule/MSM142_StJohns_schedule.nc --start-index 1 --start-time "2026-04-30 12:00" --duration 180 --format waypoints --current-position 47.5615,-52.7126 --output route/Stationsplan28.txt
cruiseplan stationplan --schedule schedule/MSM142_StJohns_schedule.nc --start-index 2 --start-time "2026-05-05 08:00" --duration 24 --current-position 65.0268,-31.3702 --format waypoints --output-dir route --output Stationsplan28.txt

cruiseplan stationplan --schedule schedule/MSM142_StJohns_schedule.nc --start-index 2 --start-time "2026-05-05 08:00" --duration 24  --current-position 65.0268,-31.3702 --format tex --logo config/images/mixsed_logo_coarse.png --title "MSM142" --number "28" --output-dir route --output Stationsplan28.tex
