// RailSense Structural Axle Box Protective Housing Matrix
$fn = 60;

inner_x = 42;
inner_y = 68;
inner_z = 26;
wall = 3.5;

module industrial_chassis() {
    difference() {
        // External Solid Shell
        minkowski() {
            cube([inner_x + 2*wall, inner_y + 2*wall, inner_z + wall]);
            cylinder(r=2, h=0.1);
        }
        
        // Internal Microcontroller Pocket Cavity
        translate([wall, wall, wall])
            cube([inner_x, inner_y, inner_z + 10]);
        
        // High-Vibration M5 Direct Mechanical Mount Flange Openings
        translate([-5, (inner_y+2*wall)/2, inner_z/2]) 
            rotate([0, 90, 0]) cylinder(h=inner_x+25, d=5.5);
            
        // Threaded Conduit Port for Shielded Sensor Cable Routing
        translate([(inner_x+2*wall)/2, inner_y+wall+2, inner_z/2])
            rotate([90, 0, 0]) cylinder(h=12, d=14);
    }
    
    // Internal PCB Anchor Isolation Mount standoffs
    translate([wall+4, wall+4, wall]) base_standoff();
    translate([wall+inner_x-4, wall+4, wall]) base_standoff();
    translate([wall+4, wall+inner_y-4, wall]) base_standoff();
    translate([wall+inner_x-4, wall+inner_y-4, wall]) base_standoff();
}

module base_standoff() {
    difference() {
        cylinder(h=6, d=7);
        cylinder(h=8, d=2.5); // Sized accurately for self-tapping assembly screws
    }
}

industrial_chassis();
