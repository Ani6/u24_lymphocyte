# Usage:
#       python gen_json_multipleheat_v3.py prediction-TCGA-xxxx lymphocyte_4 luad /data01/tcga_data/tumor/luad/ lym 0.5 necrosis 0.5

import subprocess
import numpy as np
import math
import json
import sys
import datetime
import random
import os
from bson import json_util

is_shifted = False;
shifted_x = 0;
shifted_y = 0;

def get_value(info, keyword):
    start_pos = info.find(keyword);
    first_quote_pos = info.find('\'', start_pos);
    secon_quote_pos = info.find('\'', first_quote_pos + 1);
    return info[(first_quote_pos + 1):secon_quote_pos];

n_argv = len(sys.argv);
filename = sys.argv[1];
heatmap_name = sys.argv[2];
slide_type = sys.argv[3];
svs_img_folder = sys.argv[4];

start_id_multiheat = 5;
n_heat = (n_argv - start_id_multiheat) / 2;
heat_list = [];
weight_list = [];
for h_id, h_name in enumerate(sys.argv[start_id_multiheat::2]):
    heat_list.append(h_name);
    weight_list.append(sys.argv[(start_id_multiheat+1)+2*h_id]);

print "heatnamelist, weightlist: ", heat_list, weight_list;

casename = filename.split('prediction-')[1].split('.low_res')[0];
imgfilename = svs_img_folder + '/' + casename + '.svs';

heatmapfile = 'heatmap_' + filename.split('prediction-')[1] + '.json';
metafile = 'meta_' + filename.split('prediction-')[1] + '.json';

info = subprocess.check_output(["openslide-show-properties", imgfilename]);

objective = get_value(info, 'openslide.objective-power');
mpp_x = get_value(info, 'openslide.mpp-x');
mpp_y = get_value(info, 'openslide.mpp-y');
slide_width_openslide = get_value(info, 'openslide.level[0].width');
slide_height_openslide = get_value(info, 'openslide.level[0].height');
caseid = casename[:23];   # take 23 first letters
uri = casename;
cancertype = slide_type;

print objective;
print slide_width_openslide;
print slide_height_openslide;

analysis_execution_id = 'highlym';
x_arr = np.zeros(10000000, dtype=np.float64);
y_arr = np.zeros(10000000, dtype=np.float64);
score_arr = np.zeros(10000000, dtype=np.float64);
score_set_arr = np.zeros(shape=(10000000, n_heat), dtype=np.float64);
idx = 0;
with open(filename) as infile:
    for line in infile:
        #print line;
        parts = line.split(' ');
        x = int(parts[0]);
        y = int(parts[1]);
        score = float(parts[2]);
        score_set = [float(i) for i in parts[2:2+n_heat]];

        x_arr[idx] = x;
        y_arr[idx] = y;
        score_arr[idx] = score;
        score_set_arr[idx] = score_set;
        idx += 1;

x_arr = x_arr[:idx];
y_arr = y_arr[:idx];
score_arr = score_arr[:idx];
score_set_arr = score_set_arr[:idx];
#score_arr = 1.0 - score_arr;

patch_width = max(x_arr[1] - x_arr[0], y_arr[1] - y_arr[0]);
patch_height = patch_width;

#slide_width = np.amax(x_arr) + math.floor(patch_width / 2);
#slide_height = np.amax(y_arr) + math.floor(patch_height / 2);

slide_width = int(slide_width_openslide);
slide_height = int(slide_height_openslide);

print slide_width;
print slide_height;

x_arr = x_arr / slide_width;
y_arr = y_arr / slide_height;
patch_width = patch_width / slide_width;
patch_height = patch_height / slide_height;
patch_area = patch_width * slide_width * patch_height * slide_height;

# Form dictionary for json
dict_img = {};
#dict_img['height'] = slide_height;
#dict_img['width'] = slide_width;
#dict_img['cancer_type'] = cancertype;
#dict_img['uri'] = uri;
dict_img['case_id'] = caseid;
dict_img['subject_id'] = caseid[:12];
#dict_img['objective'] = objective;
#dict_img['mpp_y'] = mpp_y;
#dict_img['mpp_x'] = mpp_x;

dict_analysis = {};
dict_analysis['study_id'] = slide_type;
dict_analysis['execution_id'] = heatmap_name;
dict_analysis['source'] = 'computer';
dict_analysis['computation'] = 'heatmap';


if (is_shifted == True):
    shifted_x = -3*patch_width / 4.0;
    shifted_y = -3*patch_height / 4.0;
with open(heatmapfile, 'w') as f:
    for i_patch in range(idx):
        dict_patch = {};
        #dict_patch['analysis_execution_id'] = 'highlym';
        #dict_patch['x'] = x_arr[i_patch] + shifted_x;
        #dict_patch['y'] = y_arr[i_patch] + shifted_y;
        #dict_patch['tile_id'] = i_patch + 1;
        #dict_patch['loc'] = [x_arr[i_patch], y_arr[i_patch]];
        #dict_patch['w'] = patch_width;
        #dict_patch['h'] = patch_height;
        #dict_patch['normalized'] = True;
        #dict_patch['type'] = 'heatmap';
        #dict_patch['color'] = 'red';

        dict_patch['type'] = 'Feature';
        dict_patch['parent_id'] = 'self';
        dict_patch['footprint'] = patch_area;
        dict_patch['x'] = x_arr[i_patch] + shifted_x;
        dict_patch['y'] = y_arr[i_patch] + shifted_y;
        dict_patch['normalized'] = 'true';
        dict_patch['object_type'] = 'heatmap_multiple';

        x1 = dict_patch['x'] - patch_width/2;
        x2 = dict_patch['x'] + patch_width/2;
        y1 = dict_patch['y'] - patch_height/2;
        y2 = dict_patch['y'] + patch_height/2;
        dict_patch['bbox'] = [x1, y1, x2, y2];

        dict_geo = {};
        dict_geo['type'] = 'Polygon';
        dict_geo['coordinates'] = [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]];
        dict_patch['geometry'] = dict_geo;

        dict_prop = {};
        dict_prop['metric_value'] = score_arr[i_patch];
        dict_prop['metric_type'] = 'tile_dice';
        dict_prop['human_mark'] = -1;

        dict_multiheat = {};
        dict_multiheat['human_weight'] = -1;
        dict_multiheat['weight_array'] = weight_list;
        dict_multiheat['heatname_array'] = heat_list;
        dict_multiheat['metric_array'] = score_set_arr[i_patch].tolist();

        dict_prop['multiheat_param'] = dict_multiheat;
        dict_patch['properties'] = dict_prop;

        dict_provenance = {};
        dict_provenance['image'] = dict_img;
        dict_provenance['analysis'] = dict_analysis;
        dict_patch['provenance'] = dict_provenance;

        #dict_feature = {};
        #dict_feature['Area'] = patch_area;
        #dict_feature['Metric'] = score_arr[i_patch];
        #dict_feature['MetricType'] = 'dice';
        #dict_patch['features'] = dict_feature;
        #dict_patch['image'] = dict_img;

        dict_patch['date'] = datetime.datetime.now();

        json.dump(dict_patch, f, default=json_util.default);
        f.write('\n');

with open(metafile, 'w') as mf:
    dict_meta = {};
    dict_meta['color'] = 'yellow';
    dict_meta['title'] = 'Heatmap-' + heatmap_name;
    dict_meta['image'] = dict_img;

    dict_meta_provenance = {};
    dict_meta_provenance['analysis_execution_id'] = heatmap_name;
    dict_meta_provenance['study_id'] = slide_type;
    dict_meta_provenance['type'] = 'computer';
    dict_meta['provenance'] = dict_meta_provenance;

    dict_meta['submit_date'] = datetime.datetime.now();
    dict_meta['randval'] = random.uniform(0,1);

    #dict_meta['analysis_execution_id'] = 'highlym';
    #dict_meta['caseid'] = caseid;
    #dict_meta['title'] = 'Heatmap-HighLym';
    json.dump(dict_meta, mf, default=json_util.default);

