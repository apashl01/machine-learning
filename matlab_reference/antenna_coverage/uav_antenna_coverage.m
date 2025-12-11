%% UAV Antenna Coverage Analysis
% Analysis of 7 spiral antenna coverage on UAV platform
% Frequency: 9 GHz
% Coverage metric: Maximum gain available from any antenna at each direction

clear; close all; clc;

%% Parameters
freq = 9e9; % 9 GHz
c = physconst('LightSpeed');
lambda = c/freq;

% Antenna specifications
beamwidth_deg = 70; % 3dB beamwidth
gain_dBi = 2; % Gain in dBi

%% Create Spiral Antenna Pattern
% For a broad beam spiral antenna, we'll create a custom pattern
% that matches the 70-degree beamwidth specification

% Create angular grid
az = -180:1:180; % Azimuth angles (degrees)
el = -90:1:90;   % Elevation angles (degrees)

% Generate pattern - using a cardioid/hemispherical pattern for spiral antennas
% Spiral antennas have good forward gain but roll off significantly in the back hemisphere
beamwidth_rad = deg2rad(beamwidth_deg);

% Create the pattern with specified beamwidth
% Using a cardioid-like pattern: good in forward direction, poor behind
[AZ, EL] = meshgrid(az, el);

% Store for later use in coverage calculation and CSV export
AZ_orig = AZ;
EL_orig = EL;

% Calculate angle from boresight (forward direction)
theta = acos(cosd(EL) .* cosd(AZ));

% Cardioid-like pattern for spiral antenna
% Front hemisphere: broad beam, Back hemisphere: strong attenuation
% Use cosine pattern in elevation for hemispherical characteristic
elevation_factor = cosd(EL);  % Strong rolloff at high elevation angles
elevation_factor(elevation_factor < 0) = 0;  % Zero gain in back hemisphere

% Azimuth pattern - broad beam based on specified beamwidth
sigma = beamwidth_rad / (2 * sqrt(2 * log(2)));
azimuth_factor = exp(-(theta.^2) / (2 * sigma^2));

% Combine elevation and azimuth patterns
% The elevation factor creates the hemispherical characteristic
% The azimuth factor controls the beamwidth
pattern_normalized = elevation_factor .* azimuth_factor;

% Add front-to-back ratio (typical for spiral: 10-20 dB)
% Spiral antennas have some back lobe, not completely zero
front_to_back_dB = 15; % 15 dB front-to-back ratio
back_lobe_level = 10^(-front_to_back_dB/10);

% Enhance front lobe and add small back lobe
pattern_combined = pattern_normalized.^0.7 + back_lobe_level * (1 - elevation_factor);

% Don't normalize - keep actual relative levels
% Convert to dB first to preserve dynamic range
pattern_dB_relative = 10*log10(pattern_combined / max(pattern_combined(:)));

% Add antenna gain to get actual gain in dBi
pattern_dB = pattern_dB_relative + gain_dBi;

% Create antenna element
% Note: CustomAntennaElement will normalize the pattern internally
% We'll add back the actual gain values after retrieving patterns
antenna = phased.CustomAntennaElement(...
    'AzimuthAngles', az, ...
    'ElevationAngles', el, ...
    'MagnitudePattern', db2mag(pattern_dB), ...
    'PhasePattern', zeros(size(pattern_dB)));

% Store the original pattern for reference
original_pattern_dB = pattern_dB;

% Visualize single antenna pattern
figure('Position', [100 100 1200 400]);
subplot(1,3,1)
pattern(antenna, freq, 'Type', 'powerdb');
title('Single Spiral Antenna Pattern (3D)');

subplot(1,3,2)
patternAzimuth(antenna, freq, 0, 'Type', 'powerdb');
title('Elevation Cut (Az=0°)');

subplot(1,3,3)
patternElevation(antenna, freq, 0, 'Type', 'powerdb');
title('Azimuth Cut (El=0°)');

%% Export Antenna Pattern to CSV
fprintf('\nExporting antenna pattern to CSV files...\n');

% 2D Pattern Export - Azimuth Cut (Elevation = 0°)
az_export = -180:1:180;  % 1 degree resolution
el_cut = 0;  % Azimuth cut at elevation = 0

% Get the pattern values at elevation = 0
[AZ_2d, EL_2d] = meshgrid(az_export, el_cut);
pattern_2d = interp2(AZ_orig, EL_orig, original_pattern_dB, AZ_2d, EL_2d, 'linear', -50);

% Create 2D CSV file
csv_2d_filename = 'spiral_antenna_2d.csv';
fid_2d = fopen(csv_2d_filename, 'w');
fprintf(fid_2d, 'Angle (deg),Gain (dBi)\n');
for i = 1:length(az_export)
    fprintf(fid_2d, '%.1f,%.3f\n', az_export(i), pattern_2d(i));
end
fclose(fid_2d);
fprintf('2D pattern exported to: %s\n', csv_2d_filename);

% 3D Pattern Export - Full sphere
az_export_3d = -180:1:180;  % 1 degree resolution
el_export_3d = -90:1:90;    % 1 degree resolution

% Create meshgrid for 3D pattern
[AZ_3d, EL_3d] = meshgrid(az_export_3d, el_export_3d);

% Get pattern values for all angles
pattern_3d = interp2(AZ_orig, EL_orig, original_pattern_dB, AZ_3d, EL_3d, 'linear', -50);

% Create 3D CSV file in three-column format
csv_3d_filename = 'spiral_antenna_3d.csv';
fid_3d = fopen(csv_3d_filename, 'w');
fprintf(fid_3d, 'Azimuth (deg),Elevation (deg),Gain (dBi)\n');
for i = 1:numel(AZ_3d)
    fprintf(fid_3d, '%.1f,%.1f,%.3f\n', AZ_3d(i), EL_3d(i), pattern_3d(i));
end
fclose(fid_3d);
fprintf('3D pattern exported to: %s\n', csv_3d_filename);

fprintf('CSV export complete!\n\n');

%% Define Antenna Positions and Orientations
% Temporary positions - YOU WILL NEED TO UPDATE THESE with actual coordinates
% Coordinate system: X=forward, Y=right, Z=up (standard aircraft)
% Units in meters (assuming small UAV, adjust as needed)

% Placeholder UAV dimensions (adjust to your actual UAV)
uav_length = 2.0; % meters
uav_width = 1.5;  % meters

% Antenna positions [x, y, z] in meters
positions = [
    % Nose antennas (2)
    uav_length*0.4,  -0.15, 0.0;  % Nose left antenna
    uav_length*0.4,   0.15, 0.0;  % Nose right antenna
    
    % Left fuselage antennas (4 in a line along X-axis, within 10 inches = 0.254m)
    0.1,   -uav_width*0.4, 0.0;   % Left fuselage antenna 1 (forward)
    0.05,  -uav_width*0.4, 0.0;   % Left fuselage antenna 2
    -0.05, -uav_width*0.4, 0.0;   % Left fuselage antenna 3
    -0.1,  -uav_width*0.4, 0.0;   % Left fuselage antenna 4 (aft)
    
    % Right fuselage antenna (1)
    0.0,  uav_width*0.4, 0.0;     % Right fuselage antenna
];

% Antenna orientations [azimuth, elevation] in degrees
% Azimuth: 0=forward, 90=right, -90=left, 180=back
% Elevation: 0=horizontal, 90=up, -90=down
orientations = [
    % Nose antennas
    -45, 0;   % Nose left: 45 degrees left of centerline
     45, 0;   % Nose right: 45 degrees right of centerline
    
    % Left fuselage antennas (all pointing left)
    -90, 0;   % Left 1: pointing left
    -90, 0;   % Left 2: pointing left
    -90, 0;   % Left 3: pointing left
    -90, 0;   % Left 4: pointing left
    
    % Right fuselage antenna
     90, 0;   % Right: pointing right
];

num_antennas = size(positions, 1);

fprintf('Number of antennas: %d\n', num_antennas);
fprintf('Operating frequency: %.2f GHz\n', freq/1e9);
fprintf('Antenna beamwidth: %.1f degrees\n', beamwidth_deg);
fprintf('Antenna gain: %.1f dBi\n', gain_dBi);

%% Export Individual Antenna Patterns in Platform Coordinates
fprintf('\nExporting individual antenna patterns in platform coordinates...\n');

% Angular resolution for export
az_export_plat = -180:2:180;  % 2 degree resolution
el_export_plat = -90:2:90;    % 2 degree resolution

for ant_idx = 1:num_antennas
    fprintf('  Exporting antenna %d...\n', ant_idx);
    
    % Get antenna orientation
    az_rot = orientations(ant_idx, 1);
    el_rot = orientations(ant_idx, 2);
    
    % Create meshgrid for platform coordinates
    [Platform_AZ, Platform_EL] = meshgrid(az_export_plat, el_export_plat);
    
    % Transform platform coordinates to antenna-local coordinates
    % Subtract antenna pointing angles to get antenna-local view
    AZ_local = Platform_AZ - az_rot;
    EL_local = Platform_EL - el_rot;
    
    % Wrap azimuth to [-180, 180]
    AZ_local = mod(AZ_local + 180, 360) - 180;
    
    % Clip elevation to [-90, 90]
    EL_local = max(-90, min(90, EL_local));
    
    % Interpolate the antenna pattern at these local coordinates
    pattern_platform = interp2(AZ_orig, EL_orig, original_pattern_dB, AZ_local, EL_local, 'linear', -50);
    
    % Create CSV file for this antenna
    csv_filename = sprintf('antenna_%d_platform_coords.csv', ant_idx);
    fid = fopen(csv_filename, 'w');
    
    % Write header with metadata
    fprintf(fid, '# Antenna %d - Pattern in Platform Coordinates\n', ant_idx);
    fprintf(fid, '# Position (m): X=%.3f, Y=%.3f, Z=%.3f\n', ...
            positions(ant_idx, 1), positions(ant_idx, 2), positions(ant_idx, 3));
    fprintf(fid, '# Antenna Orientation: Azimuth=%.1f deg, Elevation=%.1f deg\n', ...
            az_rot, el_rot);
    fprintf(fid, '# Platform Coordinates: 0 deg Az = Nose, 90 deg Az = Right, 0 deg El = Horizon\n');
    fprintf(fid, '# Frequency: %.2f GHz\n', freq/1e9);
    fprintf(fid, '# Peak Gain: %.1f dBi\n', gain_dBi);
    fprintf(fid, '#\n');
    fprintf(fid, 'Platform_Az (deg),Platform_El (deg),Gain (dBi)\n');
    
    % Write data in three-column format
    for i = 1:numel(Platform_AZ)
        fprintf(fid, '%.1f,%.1f,%.3f\n', Platform_AZ(i), Platform_EL(i), pattern_platform(i));
    end
    
    fclose(fid);
    fprintf('    Saved: %s\n', csv_filename);
end

fprintf('Individual antenna pattern export complete!\n\n');

%% Create Conformal Array
% Create a conformal array with custom orientations
conformalArray = phased.ConformalArray(...
    'Element', antenna, ...
    'ElementPosition', positions', ...
    'ElementNormal', orientations');

%% Calculate Combined Coverage Pattern
% Create angular grid for coverage analysis
az_coverage = -180:2:180;
el_coverage = -90:2:90;
[AZ_cov, EL_cov] = meshgrid(az_coverage, el_coverage);

% Initialize coverage matrix
coverage_dB = -inf(size(AZ_cov));

% Calculate pattern for each antenna and take maximum
fprintf('Calculating combined coverage pattern...\n');

% Use the original pattern_dB directly (bypass MATLAB normalization)
[AZ_orig, EL_orig] = meshgrid(az, el);

for ant_idx = 1:num_antennas
    fprintf('  Processing antenna %d of %d...\n', ant_idx, num_antennas);
    
    % Get antenna orientation
    az_rot = orientations(ant_idx, 1);
    el_rot = orientations(ant_idx, 2);
    
    % Rotate the query points to the antenna's local frame
    % This is the inverse of rotating the pattern
    AZ_rotated = AZ_cov - az_rot;
    EL_rotated = EL_cov - el_rot;
    
    % Wrap azimuth to [-180, 180]
    AZ_rotated = mod(AZ_rotated + 180, 360) - 180;
    
    % Clip elevation to [-90, 90]
    EL_rotated = max(-90, min(90, EL_rotated));
    
    % Interpolate the original pattern (with full dB range) at the rotated points
    ant_pattern = interp2(AZ_orig, EL_orig, original_pattern_dB, AZ_rotated, EL_rotated, 'linear', -50);
    
    % Take maximum (best antenna selection)
    coverage_dB = max(coverage_dB, ant_pattern);
end

fprintf('Coverage calculation complete!\n');

%% Visualize Combined Coverage
figure('Position', [100 100 1400 800]);

% 3D spherical plot
subplot(2,2,1)
[X, Y, Z] = sph2cart(deg2rad(AZ_cov), deg2rad(EL_cov), db2mag(coverage_dB));
surf(X, Y, Z, coverage_dB);
shading interp;
colormap(jet);
colorbar;
xlabel('X'); ylabel('Y'); zlabel('Z');
title('Combined Coverage Pattern (3D) - Max Gain');
axis equal;
view(3);
caxis([min(coverage_dB(:)), max(coverage_dB(:))]);

% 2D coverage map (Az vs El)
subplot(2,2,2)
contourf(AZ_cov, EL_cov, coverage_dB, 20);
colormap(jet);
colorbar;
xlabel('Azimuth (degrees)');
ylabel('Elevation (degrees)');
title('Combined Coverage Map - Max Gain (dB)');
grid on;
hold on;
% Mark cardinal directions
plot(0, 0, 'w*', 'MarkerSize', 15, 'LineWidth', 2);
text(0, 5, 'Forward', 'Color', 'white', 'HorizontalAlignment', 'center');

% Azimuth cut at elevation = 0
subplot(2,2,3)
el_idx = find(el_coverage == 0);
plot(az_coverage, coverage_dB(el_idx, :), 'b-', 'LineWidth', 2);
grid on;
xlabel('Azimuth (degrees)');
ylabel('Gain (dB)');
title('Coverage - Azimuth Cut (Elevation = 0°)');
xlim([-180 180]);
xticks(-180:45:180);

% Elevation cut at azimuth = 0 (forward)
subplot(2,2,4)
az_idx = find(az_coverage == 0);
plot(el_coverage, coverage_dB(:, az_idx), 'r-', 'LineWidth', 2);
grid on;
xlabel('Elevation (degrees)');
ylabel('Gain (dB)');
title('Coverage - Elevation Cut (Azimuth = 0° - Forward)');
xlim([-90 90]);
xticks(-90:30:90);

%% Coverage Statistics
fprintf('\n=== Coverage Statistics ===\n');
fprintf('Maximum gain: %.2f dB\n', max(coverage_dB(:)));
fprintf('Minimum gain: %.2f dB\n', min(coverage_dB(:)));
fprintf('Mean gain: %.2f dB\n', mean(coverage_dB(:)));
fprintf('Median gain: %.2f dB\n', median(coverage_dB(:)));

% Calculate coverage above certain thresholds
thresholds = [-3, -6, -10]; % dB below peak
peak_gain = max(coverage_dB(:));
for thresh = thresholds
    coverage_fraction = sum(coverage_dB(:) >= (peak_gain + thresh)) / numel(coverage_dB);
    fprintf('Coverage within %.0f dB of peak: %.1f%%\n', abs(thresh), coverage_fraction*100);
end

%% Visualize Antenna Placement on UAV
figure('Position', [100 100 800 600]);
scatter3(positions(:,1), positions(:,2), positions(:,3), 100, 'filled');
hold on;

% Draw orientation vectors
scale = 0.2;
for i = 1:num_antennas
    % Convert orientation to direction vector
    az_rad = deg2rad(orientations(i,1));
    el_rad = deg2rad(orientations(i,2));
    
    dx = cos(el_rad) * cos(az_rad);
    dy = cos(el_rad) * sin(az_rad);
    dz = sin(el_rad);
    
    quiver3(positions(i,1), positions(i,2), positions(i,3), ...
            dx*scale, dy*scale, dz*scale, 'LineWidth', 2, 'MaxHeadSize', 1);
end

% Add labels
for i = 1:num_antennas
    text(positions(i,1), positions(i,2), positions(i,3)+0.1, ...
         sprintf('Ant %d', i), 'FontSize', 10);
end

xlabel('X (Forward) [m]');
ylabel('Y (Right) [m]');
zlabel('Z (Up) [m]');
title('Antenna Placement on UAV');
grid on;
axis equal;
view(3);
legend('Antenna', 'Pointing Direction', 'Location', 'best');

%% Load and Display UAV CAD Model
% MATLAB can import both STEP and STL files
% STL is recommended for reliable visualization

uav_cad_file = 'your_uav_model.stl'; % Replace with your STL (or STEP) file path

% Scale factor to correct STL dimensions (STL files are unitless)
% Set this to scale the STL to the correct size in meters
% For example: if STL reads as 71 units but should be 2m, use scale_factor = 2/71
scale_factor = 2.0 / 71.0;  % Adjust this ratio based on your actual STL dimensions

% Flip model orientation if needed (set to true if model is backwards)
flip_model_x = true;  % Flip front-to-back (most common issue)
flip_model_y = false; % Flip left-to-right
flip_model_z = true;  % Flip up-to-down (wings were on bottom)

if exist(uav_cad_file, 'file')
    fprintf('\nLoading UAV CAD model...\n');
    
    % Check file extension
    [~, ~, ext] = fileparts(uav_cad_file);
    
    if strcmpi(ext, '.step') || strcmpi(ext, '.stp')
        % Try to import STEP file using importGeometry (R2022b+)
        % Requires Partial Differential Equation Toolbox
        try
            gm = importGeometry(uav_cad_file);
            
            % Create figure with UAV model and antennas
            figure('Position', [100 100 1000 800]);
            
            % Plot UAV geometry
            pdegplot(gm, 'FaceAlpha', 0.7, 'FaceColor', [0.8 0.8 0.8]);
            hold on;
            
            fprintf('STEP file loaded successfully using importGeometry!\n');
            
        catch ME1
            fprintf('importGeometry failed: %s\n', ME1.message);
            fprintf('Trying alternative STEP import method...\n');
            
            % Alternative method: Try using Simscape Multibody approach
            % This works for some STEP files that aren't solid bodies
            try
                % Read STEP file and extract geometry data
                % Note: This is a simplified visualization - may not work for all STEP files
                fprintf('Alternative STEP import not fully implemented.\n');
                fprintf('Please convert your STEP file to STL format for best results.\n');
                fprintf('You can use free tools like:\n');
                fprintf('  - FreeCAD (freecad.org)\n');
                fprintf('  - Blender (blender.org)\n');
                fprintf('  - Online converters like https://www.cadexchanger.com/\n');
                return;
            catch ME2
                fprintf('Alternative STEP import also failed: %s\n', ME2.message);
                fprintf('Please convert STEP to STL and try again.\n');
                return;
            end
        end
        
    elseif strcmpi(ext, '.stl')
        % Import STL file
        vertices = [];
        faces = [];
        
        try
            % Try the standard stlread function first
            TR = stlread(uav_cad_file);
            
            % Extract vertices for dimension checking
            vertices = TR.Points;
            
            % Report dimensions
            x_range = max(vertices(:,1)) - min(vertices(:,1));
            y_range = max(vertices(:,2)) - min(vertices(:,2));
            z_range = max(vertices(:,3)) - min(vertices(:,3));
            
            fprintf('STL file loaded successfully!\n');
            fprintf('STL original dimensions: X=%.2f, Y=%.2f, Z=%.2f (unitless)\n', ...
                    x_range, y_range, z_range);
            
            % Apply scaling factor
            vertices = vertices * scale_factor;
            
            % Apply flips if needed
            if flip_model_x
                vertices(:,1) = -vertices(:,1);
            end
            if flip_model_y
                vertices(:,2) = -vertices(:,2);
            end
            if flip_model_z
                vertices(:,3) = -vertices(:,3);
            end
            
            % Report scaled dimensions
            x_range_scaled = max(vertices(:,1)) - min(vertices(:,1));
            y_range_scaled = max(vertices(:,2)) - min(vertices(:,2));
            z_range_scaled = max(vertices(:,3)) - min(vertices(:,3));
            
            fprintf('After scaling by %.6f: X=%.2f, Y=%.2f, Z=%.2f meters\n', ...
                    scale_factor, x_range_scaled, y_range_scaled, z_range_scaled);
            
            % Create figure with UAV model and antennas
            figure('Position', [100 100 1000 800]);
            
            % Plot UAV model using scaled vertices
            trisurf(TR.ConnectivityList, vertices(:,1), vertices(:,2), vertices(:,3), ...
                    'FaceColor', [0.8 0.8 0.8], 'EdgeColor', 'none', 'FaceAlpha', 0.7);
            hold on;
            
        catch ME1
            fprintf('Standard stlread failed: %s\n', ME1.message);
            fprintf('Trying alternative STL import method...\n');
            
            try
                % Alternative method: Read STL manually
                fid = fopen(uav_cad_file, 'r');
                if fid == -1
                    error('Cannot open STL file');
                end
                
                % Check if binary or ASCII
                fseek(fid, 0, 'bof');
                header = fread(fid, 80, 'uchar=>char')';
                fclose(fid);
                
                if contains(lower(header), 'solid')
                    % ASCII STL
                    fprintf('Detected ASCII STL format\n');
                    [faces, vertices, ~] = read_stl_ascii(uav_cad_file);
                else
                    % Binary STL
                    fprintf('Detected Binary STL format\n');
                    [faces, vertices, ~] = read_stl_binary(uav_cad_file);
                end
                
                % Report dimensions
                x_range = max(vertices(:,1)) - min(vertices(:,1));
                y_range = max(vertices(:,2)) - min(vertices(:,2));
                z_range = max(vertices(:,3)) - min(vertices(:,3));
                
                fprintf('STL file loaded using alternative method!\n');
                fprintf('STL original dimensions: X=%.2f, Y=%.2f, Z=%.2f (unitless)\n', ...
                        x_range, y_range, z_range);
                
                % Apply scaling factor
                vertices = vertices * scale_factor;
                
                % Apply flips if needed
                if flip_model_x
                    vertices(:,1) = -vertices(:,1);
                end
                if flip_model_y
                    vertices(:,2) = -vertices(:,2);
                end
                if flip_model_z
                    vertices(:,3) = -vertices(:,3);
                end
                
                % Report scaled dimensions
                x_range_scaled = max(vertices(:,1)) - min(vertices(:,1));
                y_range_scaled = max(vertices(:,2)) - min(vertices(:,2));
                z_range_scaled = max(vertices(:,3)) - min(vertices(:,3));
                
                fprintf('After scaling by %.6f: X=%.2f, Y=%.2f, Z=%.2f meters\n', ...
                        scale_factor, x_range_scaled, y_range_scaled, z_range_scaled);
                
                % Create figure with UAV model and antennas
                figure('Position', [100 100 1000 800]);
                
                % Plot UAV model
                patch('Faces', faces, 'Vertices', vertices, ...
                      'FaceColor', [0.8 0.8 0.8], 'EdgeColor', 'none', ...
                      'FaceAlpha', 0.7);
                hold on;
                
            catch ME2
                fprintf('Alternative STL import also failed: %s\n', ME2.message);
                fprintf('\nPlease check that:\n');
                fprintf('  1. The STL file is not corrupted\n');
                fprintf('  2. The file path is correct\n');
                fprintf('  3. You have read permissions for the file\n');
                return;
            end
        end
    else
        fprintf('Unsupported file format. Use .step, .stp, or .stl\n');
        return;
    end
    
    % Plot antennas on top of CAD model
    scatter3(positions(:,1), positions(:,2), positions(:,3), 100, 'r', 'filled');
    
    % Visualize 3D antenna patterns for each antenna
    fprintf('Generating 3D antenna pattern overlays...\n');
    
    % Pattern angular resolution (lower = smoother but slower)
    az_pattern = -180:10:180;
    el_pattern = -90:10:90;
    
    % Pattern scale factor (adjust to make patterns visible on UAV)
    pattern_scale = 0.3; % Scale patterns to be visible but not overwhelming
    
    for i = 1:num_antennas
        fprintf('  Plotting pattern for antenna %d...\n', i);
        
        % Use the original pattern directly (no MATLAB normalization)
        % Interpolate at the desired resolution
        [AZ_mesh, EL_mesh] = meshgrid(az_pattern, el_pattern);
        
        % Interpolate original pattern at desired resolution
        pat_dB = interp2(AZ_orig, EL_orig, original_pattern_dB, AZ_mesh, EL_mesh, 'linear', -50);
        
        % For radius, normalize relative to peak for shape
        pat_dB_forRadius = pat_dB - max(pat_dB(:));
        
        % Convert to linear for radius
        pat_linear = 10.^(pat_dB_forRadius/10);
        
        % Scale radius - use sqrt to compress dynamic range further
        R = sqrt(pat_linear) * pattern_scale;
        
        % Convert spherical to Cartesian
        X_local = R .* cosd(EL_mesh) .* cosd(AZ_mesh);
        Y_local = R .* cosd(EL_mesh) .* sind(AZ_mesh);
        Z_local = R .* sind(EL_mesh);
        
        % Rotate pattern according to antenna orientation
        az_rot = orientations(i, 1);
        el_rot = orientations(i, 2);
        
        % Rotation matrix for azimuth (around Z-axis)
        Rz = [cosd(az_rot), -sind(az_rot), 0;
              sind(az_rot),  cosd(az_rot), 0;
              0,             0,            1];
        
        % Rotation matrix for elevation (around Y-axis after azimuth rotation)
        Ry = [cosd(el_rot),  0, sind(el_rot);
              0,             1, 0;
             -sind(el_rot),  0, cosd(el_rot)];
        
        % Combined rotation
        R_total = Rz * Ry;
        
        % Apply rotation to all points
        for ii = 1:size(X_local, 1)
            for jj = 1:size(X_local, 2)
                point = [X_local(ii,jj); Y_local(ii,jj); Z_local(ii,jj)];
                rotated = R_total * point;
                X_local(ii,jj) = rotated(1);
                Y_local(ii,jj) = rotated(2);
                Z_local(ii,jj) = rotated(3);
            end
        end
        
        % Translate to antenna position
        X_world = X_local + positions(i, 1);
        Y_world = Y_local + positions(i, 2);
        Z_world = Z_local + positions(i, 3);
        
        % Plot the 3D pattern - use actual dB gain values for coloring
        surf(X_world, Y_world, Z_world, pat_dB, ...
             'FaceAlpha', 0.6, 'EdgeColor', 'none');
    end
    
    % Add colorbar to show actual gain levels in dBi
    colormap(jet);
    cb = colorbar;
    cb.Label.String = 'Gain (dBi)';
    
    fprintf('3D pattern visualization complete!\n');
    
    % Add colorbar to show gain levels in dB
    colormap(jet);
    cb = colorbar;
    cb.Label.String = 'Gain (dB relative to peak)';
    caxis([-20 0]); % Show -20 to 0 dB range for better color contrast
    
    fprintf('3D pattern visualization complete!\n');
    
    xlabel('X (Forward) [m]');
    ylabel('Y (Right) [m]');
    zlabel('Z (Up) [m]');
    title('UAV Model with Antenna Placement');
    axis equal;
    grid on;
    view(3);
    camlight;
    lighting gouraud;
    
else
    fprintf('\nUAV CAD file not found. Skipping 3D model visualization.\n');
    fprintf('Once you have the file, specify the file path at line 228.\n');
    fprintf('Supported formats: .step, .stp (must be solid geometry), or .stl (recommended)\n');
end

fprintf('\n=== Analysis Complete ===\n');
fprintf('Review the figures for antenna coverage visualization.\n');
fprintf('Update antenna positions in the code once you have exact coordinates.\n');

%% Figure 5: UAV Model with RX and TX Antenna Patterns
fprintf('\nGenerating Figure 5: UAV with RX and TX patterns...\n');

% TX Horn Antenna Parameters
horn_beamwidth_deg = 30;  % 30 degree beamwidth
horn_gain_dBi = 14;       % 14 dBi gain
horn_position = [uav_length*0.4 + 0.0254, 0.0, 0.0];  % 1 inch (0.0254m) ahead, centered
horn_orientation = [0, 0];  % Pointing forward

% Generate TX horn pattern (cosine^n pattern typical of horns)
% Create angular grid
az_horn = -180:1:180;
el_horn = -90:1:90;
[AZ_horn, EL_horn] = meshgrid(az_horn, el_horn);

% Horn pattern - more directive than spiral
% Use cosine^n pattern where n controls beamwidth
% Calculate n from beamwidth
beamwidth_horn_rad = deg2rad(horn_beamwidth_deg);
% For cosine^n pattern, 3dB beamwidth ≈ 2*acos(0.5^(1/n))
% Solve for n: n ≈ log(0.5) / log(cos(beamwidth/2))
n_horn = log(0.5) / log(cos(beamwidth_horn_rad/2));

% Calculate angle from boresight
theta_horn = acos(cosd(EL_horn) .* cosd(AZ_horn));

% Cosine^n pattern - very directive
pattern_horn_normalized = (cos(theta_horn)).^n_horn;

% Set realistic minimum gain level (horn typically has -30 to -40 dB nulls)
% Don't let it go below -40 dB relative to peak
min_level_dB = -40;
min_level_linear = 10^(min_level_dB/10);
pattern_horn_normalized(pattern_horn_normalized < min_level_linear) = min_level_linear;
pattern_horn_normalized(theta_horn > pi/2) = min_level_linear;  % Back hemisphere at minimum level

% Convert to dB
pattern_horn_dB_relative = 10*log10(pattern_horn_normalized / max(pattern_horn_normalized(:)));
pattern_horn_dB = pattern_horn_dB_relative + horn_gain_dBi;

fprintf('TX horn pattern generated (30° beamwidth, 14 dBi gain, -40dB nulls)\n');

% Create new figure
figure('Position', [100 100 1200 900]);

% Reload and plot UAV model
if exist(uav_cad_file, 'file')
    % Check file extension
    [~, ~, ext] = fileparts(uav_cad_file);
    
    if strcmpi(ext, '.stl')
        try
            TR = stlread(uav_cad_file);
            vertices = TR.Points * scale_factor;
            
            % Apply flips
            if flip_model_x
                vertices(:,1) = -vertices(:,1);
            end
            if flip_model_y
                vertices(:,2) = -vertices(:,2);
            end
            if flip_model_z
                vertices(:,3) = -vertices(:,3);
            end
            
            % Plot UAV model
            trisurf(TR.ConnectivityList, vertices(:,1), vertices(:,2), vertices(:,3), ...
                    'FaceColor', [0.8 0.8 0.8], 'EdgeColor', 'none', 'FaceAlpha', 0.7);
            hold on;
            
        catch
            fprintf('Could not reload STL for Figure 5\n');
        end
    end
end

% Plot RX antennas (red dots)
scatter3(positions(:,1), positions(:,2), positions(:,3), 100, 'r', 'filled');

% Plot TX antenna (green dot)
scatter3(horn_position(1), horn_position(2), horn_position(3), 150, 'g', 'filled');

% Plot RX antenna patterns (using jet colormap)
fprintf('Plotting RX antenna patterns...\n');
az_pattern = -180:10:180;
el_pattern = -90:10:90;
pattern_scale = 0.3;

for i = 1:num_antennas
    fprintf('  RX antenna %d...\n', i);
    
    [AZ_mesh, EL_mesh] = meshgrid(az_pattern, el_pattern);
    pat_dB = interp2(AZ_orig, EL_orig, original_pattern_dB, AZ_mesh, EL_mesh, 'linear', -50);
    pat_dB_forRadius = pat_dB - max(pat_dB(:));
    pat_linear = 10.^(pat_dB_forRadius/10);
    R = sqrt(pat_linear) * pattern_scale;
    
    X_local = R .* cosd(EL_mesh) .* cosd(AZ_mesh);
    Y_local = R .* cosd(EL_mesh) .* sind(AZ_mesh);
    Z_local = R .* sind(EL_mesh);
    
    % Rotate pattern
    az_rot = orientations(i, 1);
    el_rot = orientations(i, 2);
    
    Rz = [cosd(az_rot), -sind(az_rot), 0;
          sind(az_rot),  cosd(az_rot), 0;
          0,             0,            1];
    
    Ry = [cosd(el_rot),  0, sind(el_rot);
          0,             1, 0;
         -sind(el_rot),  0, cosd(el_rot)];
    
    R_total = Rz * Ry;
    
    for ii = 1:size(X_local, 1)
        for jj = 1:size(X_local, 2)
            point = [X_local(ii,jj); Y_local(ii,jj); Z_local(ii,jj)];
            rotated = R_total * point;
            X_local(ii,jj) = rotated(1);
            Y_local(ii,jj) = rotated(2);
            Z_local(ii,jj) = rotated(3);
        end
    end
    
    X_world = X_local + positions(i, 1);
    Y_world = Y_local + positions(i, 2);
    Z_world = Z_local + positions(i, 3);
    
    % Plot RX pattern with jet colormap (red tones)
    surf(X_world, Y_world, Z_world, pat_dB, ...
         'FaceAlpha', 0.5, 'EdgeColor', 'none');
end

% Plot TX horn pattern (using hot colormap for distinction)
fprintf('Plotting TX horn pattern...\n');
[AZ_horn_mesh, EL_horn_mesh] = meshgrid(az_pattern, el_pattern);
pat_horn_interp = interp2(AZ_horn, EL_horn, pattern_horn_dB, AZ_horn_mesh, EL_horn_mesh, 'linear', -50);
pat_horn_forRadius = pat_horn_interp - max(pat_horn_interp(:));
pat_horn_linear = 10.^(pat_horn_forRadius/10);
R_horn = sqrt(pat_horn_linear) * pattern_scale * 1.2;  % Slightly larger scale for visibility

X_horn_local = R_horn .* cosd(EL_horn_mesh) .* cosd(AZ_horn_mesh);
Y_horn_local = R_horn .* cosd(EL_horn_mesh) .* sind(AZ_horn_mesh);
Z_horn_local = R_horn .* sind(EL_horn_mesh);

% Horn is forward-facing, no rotation needed
X_horn_world = X_horn_local + horn_position(1);
Y_horn_world = Y_horn_local + horn_position(2);
Z_horn_world = Z_horn_local + horn_position(3);

% Plot TX pattern - store handle for separate colormap
h_tx = surf(X_horn_world, Y_horn_world, Z_horn_world, pat_horn_interp, ...
     'FaceAlpha', 0.6, 'EdgeColor', 'none');

% Set colormap for overall figure (jet for RX patterns)
colormap(jet);
cb = colorbar;
cb.Label.String = 'Gain (dBi)';

% Add legend
legend_entries = {'UAV Model', 'RX Antennas', 'TX Antenna'};
legend(legend_entries, 'Location', 'northeast');

xlabel('X (Forward) [m]');
ylabel('Y (Right) [m]');
zlabel('Z (Up) [m]');
title('UAV with RX (Spiral) and TX (Horn) Antenna Patterns');
axis equal;
grid on;
view(3);
camlight;
lighting gouraud;

fprintf('Figure 5 complete!\n');

%% Figure 6: TX Horn Antenna Coverage at Multiple Frequencies
fprintf('\nGenerating Figure 6: TX horn coverage vs frequency...\n');

% Define frequency-dependent horn parameters
% [frequency_GHz, beamwidth_deg, gain_dBi]
horn_freq_data = [
    2,  71,    7.0;
    6,  40,    11.85;
    10, 25,    14.63;
    14, 25,    13.5;
    18, 25,    14.8;
];

% Create figure with subplots
figure('Position', [100 100 1600 1000]);

for idx = 1:size(horn_freq_data, 1)
    freq_horn = horn_freq_data(idx, 1) * 1e9;  % Convert to Hz
    bw_horn = horn_freq_data(idx, 2);
    gain_horn = horn_freq_data(idx, 3);
    
    fprintf('  Generating pattern for %.0f GHz (BW=%.1f deg, Gain=%.2f dBi)...\n', ...
            freq_horn/1e9, bw_horn, gain_horn);
    
    % Generate horn pattern for this frequency
    az_horn_cov = -180:1:180;
    el_horn_cov = -90:1:90;
    [AZ_horn_cov, EL_horn_cov] = meshgrid(az_horn_cov, el_horn_cov);
    
    % Calculate n from beamwidth
    beamwidth_horn_rad = deg2rad(bw_horn);
    n_horn_cov = log(0.5) / log(cos(beamwidth_horn_rad/2));
    
    % Calculate angle from boresight
    theta_horn_cov = acos(cosd(EL_horn_cov) .* cosd(AZ_horn_cov));
    
    % Cosine^n pattern
    pattern_horn_cov = (cos(theta_horn_cov)).^n_horn_cov;
    
    % Set realistic minimum gain level (-40 dB relative to peak)
    min_level_dB = -40;
    min_level_linear = 10^(min_level_dB/10);
    pattern_horn_cov(pattern_horn_cov < min_level_linear) = min_level_linear;
    pattern_horn_cov(theta_horn_cov > pi/2) = min_level_linear;
    
    % Convert to dB
    pattern_horn_dB_rel = 10*log10(pattern_horn_cov / max(pattern_horn_cov(:)));
    horn_coverage_dB = pattern_horn_dB_rel + gain_horn;
    
    % Plot in subplot (2 rows, 3 columns, but only use 5 subplots)
    if idx <= 3
        subplot(2, 3, idx);
    else
        subplot(2, 3, idx + 1);  % Skip middle position of bottom row
    end
    
    % 2D coverage map (Az vs El)
    contourf(AZ_horn_cov, EL_horn_cov, horn_coverage_dB, 20);
    colormap(jet);
    colorbar;
    xlabel('Azimuth (degrees)');
    ylabel('Elevation (degrees)');
    title(sprintf('TX Horn at %.0f GHz\nBW=%.1f°, Gain=%.2f dBi', ...
                  freq_horn/1e9, bw_horn, gain_horn));
    grid on;
    hold on;
    % Mark forward direction
    plot(0, 0, 'w*', 'MarkerSize', 15, 'LineWidth', 2);
    text(0, 5, 'Fwd', 'Color', 'white', 'HorizontalAlignment', 'center', 'FontSize', 8);
    caxis([gain_horn-40, gain_horn]);  % Consistent color scale per subplot
end

% Add overall title
sgtitle('TX Horn Antenna Coverage vs Frequency', 'FontSize', 14, 'FontWeight', 'bold');

fprintf('Figure 6 complete!\n');

%% Helper Functions for STL Reading

function [F, V, N] = read_stl_binary(filename)
    % Read binary STL file
    fid = fopen(filename, 'r');
    if fid == -1
        error('Cannot open file');
    end
    
    % Skip header
    fseek(fid, 80, 'bof');
    
    % Read number of triangles
    num_triangles = fread(fid, 1, 'uint32');
    
    % Preallocate arrays
    V = zeros(num_triangles * 3, 3);
    F = reshape(1:(num_triangles * 3), 3, num_triangles)';
    N = zeros(num_triangles, 3);
    
    % Read each triangle
    for i = 1:num_triangles
        % Normal vector
        N(i, :) = fread(fid, 3, 'float32')';
        % Vertices
        v1 = fread(fid, 3, 'float32')';
        v2 = fread(fid, 3, 'float32')';
        v3 = fread(fid, 3, 'float32')';
        V((i-1)*3 + 1, :) = v1;
        V((i-1)*3 + 2, :) = v2;
        V((i-1)*3 + 3, :) = v3;
        % Skip attribute byte count
        fread(fid, 1, 'uint16');
    end
    
    fclose(fid);
end

function [F, V, N] = read_stl_ascii(filename)
    % Read ASCII STL file
    fid = fopen(filename, 'r');
    if fid == -1
        error('Cannot open file');
    end
    
    vertices = [];
    normals = [];
    
    while ~feof(fid)
        line = fgetl(fid);
        if contains(line, 'facet normal')
            % Read normal
            parts = strsplit(strtrim(line));
            normal = [str2double(parts{3}), str2double(parts{4}), str2double(parts{5})];
            normals = [normals; normal];
            
            % Skip "outer loop"
            fgetl(fid);
            
            % Read 3 vertices
            for j = 1:3
                vertex_line = fgetl(fid);
                parts = strsplit(strtrim(vertex_line));
                vertex = [str2double(parts{2}), str2double(parts{3}), str2double(parts{4})];
                vertices = [vertices; vertex];
            end
            
            % Skip "endloop" and "endfacet"
            fgetl(fid);
            fgetl(fid);
        end
    end
    
    fclose(fid);
    
    num_triangles = size(vertices, 1) / 3;
    V = vertices;
    F = reshape(1:size(V, 1), 3, num_triangles)';
    N = normals;
end
