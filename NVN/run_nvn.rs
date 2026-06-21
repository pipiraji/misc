// ==============================================================
// Auto-Generated IC Validator NVN Runset
// ==============================================================
#include <icv.rh>

lay = read_layout_netlist(
    layout_file = {{filename = "test_inputs\target.sp", format = SPICE}}
);

sch = schematic(
    schematic_file = {{filename = "test_inputs\reference.sp", format = SPICE}}
);

compare_state = init_compare_matrix(
    netlist_vs_netlist = PARTIAL_RUNSET
);

// --- 기생 성분 필터링 ---
filter(compare_state, CAPACITOR, {"*"}, filter_options(filter_type = FILTER_OPEN));
filter(compare_state, RESISTOR,  {"*"}, filter_options(filter_type = FILTER_SHORT));

// --- map_gendev: GENERIC device 매핑 (terminals 필수) ---
// 매뉴얼: map_gendev(state, device_name="...", terminals={{pin_name="...", pin_compared=true}, ...})
map_gendev(compare_state,
    device_name = "inv",
    terminals   = {{pin_name = "in", pin_compared = true}, {pin_name = "out", pin_compared = true}, {pin_name = "vdd", pin_compared = true}, {pin_name = "vss", pin_compared = true}}
);

map_gendev(compare_state,
    device_name = "nand",
    terminals   = {{pin_name = "a", pin_compared = true}, {pin_name = "b", pin_compared = true}, {pin_name = "out", pin_compared = true}, {pin_name = "vss", pin_compared = true}}
);

map_gendev(compare_state,
    device_name = "withquote",
    terminals   = {{pin_name = "in", pin_compared = true}, {pin_name = "out", pin_compared = true}, {pin_name = "vss", pin_compared = true}}
);

// --- check_property: 파라미터 허용 오차 0 (완전 일치) ---
check_property(compare_state, GENERIC, {"inv"},
    property_tolerances = {{"l", [0, 0], ABSOLUTE}, {"w", [0, 0], ABSOLUTE}}
);

check_property(compare_state, GENERIC, {"nand"},
    property_tolerances = {{"w", [0, 0], ABSOLUTE}}
);

check_property(compare_state, GENERIC, {"withquote"},
    property_tolerances = {{"param1", [0, 0], ABSOLUTE}, {"size", [0, 0], ABSOLUTE}}
);

compare(compare_state, sch, lay,
    schematic_top_cell = "TOP",
    layout_top_cell    = "TOP"
);
