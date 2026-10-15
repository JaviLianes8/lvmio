# lvmio 1.0.0 author mutation round 5, mutant by mutant

Round 5 of the author mutation rounds (see CERT-1.0-REPORT.md, item 18), at 1d0436e: each
mutation applied alone, the whole suite run, the first failing test recorded.

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | fixed notation from 1e-5 | `_number.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M02 | fixed notation up to 1e8 | `_number.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvmio._number]` |
| M03 | 1e7 itself in fixed notation | `_number.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvmio._number]` |
| M05 | exponent padded to two digits | `_number.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M06 | NaN spelled nan | `_number.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M07 | negative infinity spelled -inf | `_number.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvmio._number]` |
| M08 | X0 with 15 decimals | `_number.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M09 | decimal comma not converted | `_number.py` | killed | `tests/test_cli_edges.py::test_encoding_option_is_applied_and_checked` |
| M10 | grammar check skipped (float decides) | `_number.py` | killed | `tests/test_cli_edges.py::test_a_windows_1252_file_is_read_without_an_encoding` |
| M11 | Infinity spelling unknown | `_number.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[read/token_17.lvm]` |
| M12 | sign of special values dropped | `_number.py` | killed | `tests/test_cli_edges.py::test_json_dump_stays_valid_json_with_infinities` |
| M13 | any Unicode blank stripped | `_number.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[read/token_36.lvm]` |
| M14 | two signs accepted on specials | `_number.py` | killed | `tests/test_number.py::test_parse_number_refuses_everything_else[++inf]` |
| M15 | header cells not shifted for the X column | `_segment.py` | killed | `tests/test_contract.py::test_empty_fields_become_nan` |
| M16 | Comment column read as a channel | `_segment.py` | killed | `tests/test_cli_edges.py::test_a_windows_1252_file_is_read_without_an_encoding` |
| M17 | X_Value columns read as channels | `_segment.py` | killed | `tests/test_cli_edges.py::test_multi_x_columns_dump` |
| M18 | empty cell read as zero | `_segment.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[read/empty_last_row.lvm]` |
| M19 | repeated file header parsed as a segment | `_read.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[appended_runs.lvm]` |
| M20 | segment header without its end marker tolerated | `_segment.py` | killed | `tests/test_review_edges2.py::test_a_header_block_without_its_end_marker_is_refused[LabVIEW` |
| M21 | Latin-1 instead of Windows-1252 | `_read.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[comment_cp1252.lvm]` |
| M22 | Multi_Headings never read | `_read.py` | killed | `tests/test_contract.py::test_lvmfile_iterates_segments_and_reports_multi_headings` |
| M23 | comma decimal in a comma file accepted as a separator | `_read.py` | killed | `tests/test_review_edges.py::test_only_a_period_or_a_comma_is_a_decimal_separator` |
| M24 | comma separator never detected | `_read.py` | killed | `tests/test_contract.py::test_parse_lvm_matches_read_lvm_on_the_same_bytes` |
| M25 | no separator line after the file header | `_render.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M26 | Multi header width one short | `_render.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M27 | Y_Unit_Label always written | `_render.py` | killed | `tests/test_contract_edges.py::test_a_bad_header_number_names_its_own_line` |
| M28 | Multi_Headings Yes for one segment | `_render.py` | killed | `tests/test_contract.py::test_lvmfile_iterates_segments_and_reports_multi_headings` |
| M29 | X values written in No files | `_render.py` | killed | `tests/test_labview_captures.py::test_rewriting_a_labview_file_gives_back_its_exact_bytes[express_default.lvm]` |
| M30 | comment on every row | `_render.py` | killed | `tests/test_docs.py::test_pycon_examples_run[README.md]` |
| M31 | Multi X cells from the first channel | `_render.py` | killed | `tests/test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M32 | Delta_X follows a precision below 6 | `_render.py` | killed | `tests/test_labview_delta_x.py::test_delta_x_keeps_six_decimals_at_a_low_precision` |
| M33 | bool accepted as a sample | `_check.py` | killed | `tests/test_validation.py::test_bad_data_is_refused[data6-TypeError]` |
| M34 | reserved channel names accepted | `_check.py` | killed | `tests/test_validation.py::test_bad_data_is_refused[data17-ValueError]` |
| M35 | separator inside a field accepted | `_check.py` | killed | `tests/test_review_edges.py::test_text_subclasses_cannot_change_what_is_checked_or_written` |
| M36 | comma as separator and decimal accepted | `_check.py` | killed | `tests/test_validation.py::test_bad_data_is_refused[data29-ValueError]` |
| M37 | precision up to 30 accepted | `_write.py` | killed | `tests/test_validation.py::test_bad_keywords_are_refused[kwargs1-ValueError]` |
| M38 | file opened before the data is checked | `_write.py` | killed | `tests/test_review_edges4.py::test_an_encoding_that_fails_without_a_position_names_no_character[idna]` |
| M39 | CSV rows end with CRLF again | `_cli_output.py` | killed | `tests/test_cli_edges.py::test_multi_x_columns_dump` |
| M40 | infinity left as a float in JSON | `_cli_output.py` | killed | `tests/test_cli_edges.py::test_json_dump_stays_valid_json_with_infinities` |
| M41 | closed pipe not handled | `_cli.py` | killed | `tests/test_contract_edges.py::test_a_closed_output_pipe_exits_zero_and_silently` |
| M42 | channel name in the error not shortened | `_cli.py` | killed | `tests/test_contract_edges.py::test_a_huge_unknown_channel_name_is_not_echoed` |
| M43 | time axis one sample long | `_model.py` | killed | `tests/test_cli_edges.py::test_json_dump_stays_valid_json_with_infinities` |
| M44 | get returns the last match | `_model.py` | killed | `tests/test_contract_edges.py::test_get_returns_the_first_of_two_channels_with_one_name` |
| M45 | comment escapes not decoded | `_segment.py` | killed | `tests/test_contract_more.py::test_lower_case_hex_escapes_in_comments_are_decoded` |
| M46 | byte order mark kept | `_read.py` | killed | `tests/test_contract_edges.py::test_a_byte_order_mark_is_ignored` |
| M47 | messages quote the whole input | `_number.py` | killed | `tests/test_cli_edges.py::test_a_huge_bad_cell_is_not_echoed_back` |
| M48 | segment rows run into the next segment header | `_segment.py` | killed | `tests/test_contract_edges.py::test_a_segment_may_follow_the_rows_without_a_blank_line` |
| M49 | stdin decoded with the default encoding | `_cli.py` | killed | `tests/test_contract_edges.py::test_standard_input_utf8_is_not_read_in_the_locale_encoding` |
| M50 | encoding option ignored for files | `_cli.py` | killed | `tests/test_cli_edges.py::test_encoding_option_is_applied_and_checked` |
| M51 | fixed ties rounded to even | `_number.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvmio._number]` |
| M52 | exponent ties all rounded away from zero | `_number.py` | killed | `tests/test_labview_numbers.py::test_labview_number_format_on_every_captured_value[exponent_ties]` |
| M53 | notation from the rounded value, not log10 in double | `_number.py` | killed | `tests/test_labview_delta_x.py::test_x_cells_at_near_ties_differ_by_one_unit_in_the_last_decimal` |
| M54 | mantissa carry not handled | `_number.py` | killed | `tests/test_labview_numbers.py::test_labview_number_format_on_every_captured_value[ties]` |
| M55 | backslash not doubled | `_comment.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvmio._comment]` |
| M56 | control codes in lower-case hex | `_comment.py` | killed | `tests/test_contract_more.py::test_cli_channels_escapes_control_characters` |
| M57 | comma not escaped in comma files | `_comment.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvmio._comment]` |
| M58 | DEL escaped | `_comment.py` | killed | `tests/test_labview_captures.py::test_rewriting_a_labview_file_gives_back_its_exact_bytes[comments.lvm]` |
| M59 | short rows padded again | `_segment.py` | killed | `tests/test_hostile.py::test_seeded_mutations_raise_only_lvm_error` |
| M60 | data row after a blank line read as a header | `_read.py` | killed | `tests/test_contract_more.py::test_a_row_with_an_empty_first_cell_after_a_blank_line_is_refused` |
| M61 | finite Decimal overflow written as Inf | `_check.py` | killed | `tests/test_review_edges.py::test_a_finite_decimal_too_large_for_a_double_is_refused` |
| M62 | sets and mappings accepted as samples | `_check.py` | killed | `tests/test_review_edges.py::test_unordered_samples_are_refused[values0]` |
| M63 | comment allowed on an empty segment | `_check.py` | killed | `tests/test_review_edges.py::test_a_comment_needs_a_row` |
| M64 | only space and tab count as blanks in fields | `_check.py` | killed | `tests/test_review_edges.py::test_any_surrounding_blank_is_refused_so_text_reads_back_unchanged[\xa0]` |
| M65 | text subclasses used as given | `_check.py` | killed | `tests/test_review_edges.py::test_text_subclasses_cannot_change_what_is_checked_or_written` |
| M66 | redirected output in the locale encoding | `_cli.py` | killed | `tests/test_contract_edges.py::test_redirected_output_is_utf8_and_csv_spells_infinity` |
| M67 | CSV infinity as Python spells it | `_cli_output.py` | killed | `tests/test_contract_edges.py::test_redirected_output_is_utf8_and_csv_spells_infinity` |
| M68 | public classes keep their private module | `__init__.py` | killed | `tests/test_contract_edges.py::test_public_classes_report_the_public_module` |
| M69 | comment on a later row does not start a segment | `_split.py` | killed | `tests/test_review_edges3.py::test_a_comment_on_a_later_row_starts_a_segment_even_when_x_continues` |
| M70 | X jumps do not start a segment | `_split.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[one_header_gap.lvm]` |
| M71 | no slack for printed digits | `_split.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[delta_x_1e-7.lvm]` |
| M72 | no slack for double rounding | `_split.py` | killed | `tests/test_review_edges3.py::test_a_large_x0_at_full_precision_stays_one_segment` |
| M73 | a later write keeps the header increment | `_split.py` | killed | `tests/test_labview_headers.py::test_a_later_write_that_jumps_or_changes_step_keeps_its_x_axis` |
| M74 | Samples trimming drops non-empty cells | `_split.py` | killed | `tests/test_hostile.py::test_seeded_mutations_raise_only_lvm_error` |
| M75 | no Samples trimming | `_split.py` | killed | `tests/test_contract.py::test_empty_fields_become_nan` |
| M76 | later segments start at the header X0 | `_segment.py` | killed | `tests/test_labview_headers.py::test_a_later_write_that_jumps_or_changes_step_keeps_its_x_axis` |
| M77 | channel dates taken from the first channel | `_segment.py` | killed | `tests/test_labview_headers.py::test_each_channel_keeps_its_own_date_and_time` |
| M78 | notes not read | `_segment.py` | killed | `tests/test_labview_headers.py::test_relays_and_notes_survive_a_rewrite` |
| M79 | empty X_Dimension cell read as Time | `_segment.py` | killed | `tests/test_labview_relay.py::test_labview_keeps_only_the_time_and_frequency_dimensions` |
| M80 | X cells not checked | `_segment.py` | survived | none: equivalent once every X column is parsed while splitting; the check was removed in b3c1119 |
| M81 | description not written | `_render.py` | killed | `tests/test_labview_captures.py::test_rewriting_a_labview_file_gives_back_its_exact_bytes[description.lvm]` |
| M82 | notes not written | `_render.py` | killed | `tests/test_labview_headers.py::test_relays_and_notes_survive_a_rewrite` |
| M83 | channel dates not written | `_render.py` | killed | `tests/test_labview_headers.py::test_each_channel_keeps_its_own_date_and_time` |
| M84 | non-finite increments accepted | `_check.py` | killed | `tests/test_review_edges3.py::test_a_non_finite_delta_x_is_refused` |
| M85 | channel data kept as given | `_model.py` | killed | `tests/test_review_edges3.py::test_a_channel_keeps_any_iterable_as_a_list` |
| M86 | description not decoded | `_read.py` | killed | `tests/test_labview_captures.py::test_rewriting_a_labview_file_gives_back_its_exact_bytes[description.lvm]` |
| M87 | description blanks accepted | `_check.py` | killed | `tests/test_review_edges3.py::test_a_description_with_blanks_at_either_end_is_refused[` |
| M88 | a row of empty cells ends the segment | `_segment.py` | killed | `tests/test_labview_layouts.py::test_a_row_of_empty_cells_is_a_row_of_missing_samples` |
| M89 | a blank line in the file header tolerated | `_read.py` | killed | `tests/test_labview_captures.py::test_lvmio_reads_what_labview_reads[read/blank_in_file_header.lvm]` |
| M90 | the header command prints the raw description | `_cli_output.py` | killed | `tests/test_review_edges3.py::test_the_header_text_escapes_a_description_with_a_line_break` |
| M91 | a step of zero adopted | `_split.py` | killed | `tests/test_labview_headers.py::test_later_writes_with_a_small_step_change_or_one_row_each_are_kept_apart` |
| M92 | a step adopted without the next row agreeing | `_split.py` | killed | `tests/test_review_edges3.py::test_a_one_row_write_does_not_lend_the_next_write_its_step` |
| M93 | a 25 percent allowance on the step | `_split.py` | killed | `tests/test_labview_headers.py::test_later_writes_with_a_small_step_change_or_one_row_each_are_kept_apart` |
| M94 | rounding allowance ignores the write's origin | `_split.py` | killed | `tests/test_review_edges4.py::test_an_axis_heading_toward_zero_stays_one_segment[14--0.001-1e-06-3000]` |
| M95 | only the first X column checked for jumps | `_split.py` | killed | `tests/test_review_edges4.py::test_a_jump_in_a_later_multi_x_column_starts_a_segment` |
| M96 | padding trimmed in no write after a split | `_segment.py` | killed | `tests/test_review_edges4.py::test_samples_padding_of_the_first_write_is_trimmed_when_a_later_write_follows` |
| M97 | a codec failure always names a character | `_write.py` | killed | `tests/test_review_edges4.py::test_an_encoding_that_fails_without_a_position_names_no_character[idna]` |
| M98 | the caller's decimal context used | `_number.py` | killed | `tests/test_labview_numbers.py::test_labview_number_format_on_every_captured_value[ties]` |
| M99 | the shared X column follows the first channel only | `_cli_output.py` | killed | `tests/test_contract_more.py::test_cli_csv_shared_time_column_spans_the_longest_channel` |
| M100 | one X column whatever the channels' axes | `_cli_output.py` | killed | `tests/test_contract_more.py::test_cli_csv_time_columns_follow_each_channel` |
| M101 | channel names printed raw | `_cli_output.py` | killed | `tests/test_contract_more.py::test_cli_channels_escapes_control_characters` |
