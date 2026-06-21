* Target netlist for NVN generator test
.subckt TOP net1 net2 vdd vss
M_core net1 net2 vdd vss nch w=2u l=0.06u
R_pullup vdd net1 1k
.ends
