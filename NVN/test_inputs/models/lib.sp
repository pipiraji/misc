* Sample SPICE library for testing

.subckt INV in out vdd vss W=1 L=0.06u
M1 out in vdd vss nch w={W} l={L}
.ends

.subckt NAND a b out vss W=2
M1 out a vdd vss nch w=2u l=0.06u
+ M2 out b vdd vss nch w=2u l=0.06u
.ends

.subckt WITHQUOTE in out vss param1='a=1' size=5
M1 out in vss vss nch w=5u l=0.06u
.ends

.subckt TOP net1 net2 vdd vss
XINV net1 net2 vdd vss INV W=1
.ends
