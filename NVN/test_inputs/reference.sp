* Reference netlist for NVN generator test
.subckt TOP net1 net2 vdd vss
M_core_ref net1 net2 vdd vss nch w=2u l=0.06u
C_load net2 0 0.1f
.ends
