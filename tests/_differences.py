"""Where lvmio and LabVIEW's reader do not read the same thing; GUIDE.md lists each case.

Token files are known by their cell, every other file by its path under labview2026.
"""

from __future__ import annotations

# LabVIEW reads these cells by their longest numeric prefix (or a blank line as a row);
# lvmio refuses them instead of returning part of the text. GUIDE.md lists them.
LABVIEW_READS_LVMIO_REFUSES = {
    "0x10",
    "1_0",
    "1,5",
    "2.5V",
    "1.5e",
    "1d5",
    "Inf5",
    "NaN1",
    "1E5.5",
    "1.#INF",
    "nan(ind)",
    "0b1",
    "1e5e5",
    "Infinite",
    "infinityx",
    "1 2",
    chr(12) + "1",
    chr(12) + "1" + chr(12),
    " " + chr(12) + "2.5",
    "- 1",
    "+ 2",
    "- Inf",
    "1e+ 5",
    "read/blank_line_in_rows.lvm",
    "read/blank_in_file_header.lvm",
    "read/spaces_line_in_file_header.lvm",
    "read/blank_in_segment_header.lvm",
    "read/blank_before_column_line.lvm",
    "read/text_delta_x.lvm",
    "read/comment_cells.lvm",
    "one_header_fewer.lvm",
    "one_header_more.lvm",
}
# LabVIEW refuses these (error 100); lvmio reads them. GUIDE.md lists them.
LVMIO_READS_LABVIEW_REFUSES = {
    "-nan",
    "+NaN",
    "   ",
    "read/no_x_value_column.lvm",
    "read/period_cell_in_comma_file.lvm",
    "read/samples_missing.lvm",
    "read/channels_more_than_columns.lvm",
    "read/no_x0_line.lvm",
    "read/no_delta_x_line.lvm",
    "read/x0_key_with_space.lvm",
    "read/byte_order_mark.lvm",
    "read/no_date_time_lines.lvm",
}
# Both read a value but not the same one: LabVIEW truncates its own writer's periods in a
# file declaring a comma, and reads some cells one unit in the last place away
# (test_labview_numbers.py pins those).
READ_DIFFERENTLY = {
    "period_decimal.lvm",
    "read/lvmio_ulp.lvm",
    "read/samples_more_than_rows.lvm",
    "read/samples_fewer_than_rows.lvm",
    "read/samples_blank.lvm",
    "read/channels_key_with_space.lvm",
    "read/empty_middle_row.lvm",
    "read/samples_more_than_rows_no_x.lvm",
    "read/samples_more_than_rows_multi.lvm",
    "one_header_same.lvm",
    "read/samples_more_multi_two_channels.lvm",
}
# LabVIEW files that change on a rewrite, each for a reason GUIDE.md gives: seven-digit
# rounding across a notation boundary, and X cells rebuilt from Delta_X.
REWRITE_BOUNDARY = {
    "ties.lvm",
    "near_ties.lvm",
    "delta_x_2048hz.lvm",
    "delta_x_1e-7.lvm",
    "x0_offsets.lvm",
    "one_header_same.lvm",
    "one_header_fewer.lvm",
    "one_header_more.lvm",
}
