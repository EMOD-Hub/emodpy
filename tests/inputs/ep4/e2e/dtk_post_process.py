#!/usr/bin/python

import os
import json
import emod_api.config.dtk_post_process_adhocevents as dpp
import emod_api.spatialreports.spatial as sr


def calc_prev_diff_bw_nodes(output_path):
    try:
        print("calc_prev_diff_bw_nodes: creating report_path...")
        report_path = os.path.join(output_path, "SpatialReport_Prevalence.bin")
        print(f"calc_prev_diff_bw_nodes: opening {report_path}...")
        if not os.path.exists(report_path):
            raise ValueError(f"Failed to find {report_path}.")
        data = sr.SpatialReport(report_path)
        print("calc_prev_diff_bw_nodes: Opened data...")
        if not data:
            raise ValueError("Found no spatial data in report.")
        final_node_prev_values = []
        print(f"calc_prev_diff_bw_nodes: Looping over nodes: {data.node_ids}...")
        for node_id in data.node_ids:      # assume 1 and 2
            print("calc_prev_diff_bw_nodes: Getting chan_data...")
            chan_data = data[node_id].data
            print("calc_prev_diff_bw_nodes: Appending last value...")
            final_node_prev_values.append(chan_data[-1])
        print("calc_prev_diff_bw_nodes: Returning diff...")
        print(f"calc_prev_diff_bw_nodes: diff = {abs(final_node_prev_values[-1] - final_node_prev_values[0])}.")
        return abs(final_node_prev_values[-1] - final_node_prev_values[0])
    except Exception as ex:
        print(str(ex))


def application(output_path):
    if os.path.exists("config_xform.json") is False:
        return
    dpp.application(output_path)

    # Find final prevalence and write to new file.
    with open(os.path.join(output_path, "InsetChart.json")) as fp:
        icj = json.loads(fp.read())
    final_prev = icj["Channels"]["Infected"]["Data"][-1]
    with open(os.path.join(output_path, "final_prev"), "w") as fp:
        fp.write(str(final_prev))

    node_prev_final_delta = calc_prev_diff_bw_nodes(output_path)
    with open(os.path.join(output_path, "final_prev_node_diff"), "w") as fp:
        fp.write(str(node_prev_final_delta))

    print("dtk_post_process.py ran!")


if __name__ == "__main__":
    # execute only if run as a script
    application("config.json")
