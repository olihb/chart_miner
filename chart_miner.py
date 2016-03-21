from bokeh.client.session import push_session
from bokeh.document import Document
from bokeh.models.widgets.inputs import TextInput
from bokeh.models.widgets.tables import DataTable, TableColumn

__author__ = 'olihb'


import json
import sys
import numpy as np
from numpy import pi

from bokeh.plotting import figure, output_file, show, ColumnDataSource
from bokeh import palettes
from bokeh.models import HoverTool,HBox, VBox, Select
from bokeh.models.widgets import Dropdown
from bokeh.io import output_file, show, vform, curdoc, curstate
from bokeh.charts import Bar, Scatter
import pandas as pd
from bokeh.models.renderers import GlyphRenderer
import pandas.core.series

curstate().autoadd = False
session = push_session(curdoc())

# read json file
with open('data/content_data.json') as datafile:
    input_data = json.load(datafile)

# extract attribute names
data = input_data['data']
data_attributes = map(lambda a: a['attributes'], data)
attributes_name = list(set([item['name'] for sublist in data_attributes for item in sublist]))

# global state
selected_attribute = attributes_name[1]
selected_points = []
table_selected_attribute=selected_attribute
threshold = 10
current_indices = []

# utility functions
def calculate_ratio(input_df):
    ratio_df = (input_df.div(context_df,level='attr_value').dropna()*100).sort_values(by='n', ascending=False).rename(columns={'n': 'ratio'})
    joined_df = input_df.join(ratio_df).sort_values(by=['ratio','n'], ascending=False)
    return joined_df[joined_df.n>threshold]

def to_color(d):
    unique=d['attr_value'].unique().tolist()
    return map(lambda x: palettes.Spectral11[unique.index(x)%11], d['attr_value'])

# create attribute data source
source_data = list()
for d in data:
    point_attributes = d['attributes']
    for attributes in point_attributes:
        point_attribute_name = attributes['name']
        for idx, point_attribute_value in enumerate(attributes['values']):
            point_dict = dict (
                id = d['id'],
                x = d['x'],
                y = d['y'],
                name = d['title'],
                attr_name = point_attribute_name,
                attr_value = point_attribute_value,
                attr_rank = idx
            )
            source_data.append(point_dict)
df = pd.DataFrame(source_data)

# setup main chart
hover = HoverTool(tooltips=[("Name", "@name"),("Attribute", "@attr_value"),])
main_scatter_plot = figure(tools='box_select,lasso_select,pan,wheel_zoom,reset,resize,save')
main_scatter_plot.add_tools(hover)
main_scatter_df = df[(df.attr_rank==0) & (df.attr_name==selected_attribute) & (df.attr_rank==0)]
main_scatter_source=ColumnDataSource(main_scatter_df)
color = to_color(main_scatter_df)
r=main_scatter_plot.circle('x','y', source=main_scatter_source, radius=0.25, fill_alpha=0.8, color=color)

# calculate context
context_df = df.groupby(['attr_value']).agg({'id':'count'}).rename(columns={'id':'n'})

# setup attribute table
table_df = df[df.attr_name==selected_attribute].groupby(['attr_value']).agg({'id':'count'})
table_df = table_df.sort_values(by='id', ascending=False).rename(columns={'id':'n'})
joined_df = calculate_ratio(table_df)
table_source = ColumnDataSource(joined_df)
table_source_column = [TableColumn(field="attr_value", title="Attribute Value"),TableColumn(field="n", title="Counts"),TableColumn(field="ratio", title="Ratio"),]
table_data_table = DataTable(source=table_source, columns=table_source_column, width=400, height=800)

# setup dropdowns
main_dropdown = Select(title="Chart Attributes", options=attributes_name, value=selected_attribute)
table_dropdown = Select(title="Histogram Attributes", options=attributes_name, value=selected_attribute)

# setup text input
threshold_input = TextInput(value=str(threshold), title="Threshold:")

# setup layout
layout_left = VBox(main_scatter_plot, main_dropdown)
layout_right = VBox(HBox(table_dropdown,threshold_input), table_data_table)
layout = HBox(layout_left,layout_right)

def update_threshold_callback(attr_name, old, new):
    global threshold
    threshold=int(new)
    update_table()

# update main chart
def update_main_callback(attr_name, old, new):
    filtered_df = df[(df.attr_rank==0) & (df.attr_name==new) & (df.attr_rank==0)]
    for column in filtered_df:
        main_scatter_source.data[column]=filtered_df[column]
    main_scatter_source.data['fill_color']=to_color(filtered_df)
    main_scatter_source.data['line_color']=to_color(filtered_df)

# update table chart
def update_table_callback(attr_name, old, new):
    global table_selected_attribute
    table_selected_attribute = new
    update_table()

# update selection callback
def update_selection_callback(attr_name, old, new):
    global current_indices
    current_indices = new['1d']['indices']
    update_table()

# update table
def update_table():
    item_list = main_scatter_source.data['id']
    if isinstance(item_list, pandas.core.series.Series):
        item_list = item_list.values.tolist()

    if len(current_indices)>0 and len(item_list)>0:
        selected_id = list()
        for i in current_indices:
            selected_item_id = item_list[i]
            selected_id.append(selected_item_id)
        new_df = df[(df.attr_name==table_selected_attribute) & (df.id.isin(selected_id))].groupby(['attr_value']).agg({'id':'count'}).sort_values(by='id', ascending=False).rename(columns={'id':'n'})
        joined_df = calculate_ratio(new_df)
        table_source.data = ColumnDataSource._data_from_df(joined_df)
    else:
        new_df = df[(df.attr_name==table_selected_attribute)].groupby(['attr_value']).agg({'id':'count'}).sort_values(by='id', ascending=False).rename(columns={'id':'n'})
        joined_df = calculate_ratio(new_df)
        table_source.data = ColumnDataSource._data_from_df(joined_df)


# setup interactivity
r.data_source.on_change('selected', update_selection_callback)
main_dropdown.on_change('value', update_main_callback)
table_dropdown.on_change('value', update_table_callback)
threshold_input.on_change('value', update_threshold_callback)

# open the document in a browser
curdoc().add_root(layout)
session.show()
session.loop_until_closed()