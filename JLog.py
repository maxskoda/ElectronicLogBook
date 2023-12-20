from dash import Dash, dcc, html, Input, Output, State, dash_table, callback, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px

import pandas as pd
import numpy as np
from base64 import b64encode

from time import sleep
from random import randint, seed

import urllib.request
import ssl
from io import StringIO
from IPython.display import display, HTML, Image
from getpass import getpass

from mantid.simpleapi import *

# import matplotlib.pyplot as plt

#### Mantid test ###
wksp = Load(Filename=r'\\isis.cclrc.ac.uk\inst$\ndxinter\instrument\data\cycle_23_4\INTER00071612.raw',
            OutputWorkspace='INTER00071612')
print(wksp.getRun().getLogData('THETA').value[-1])

# Detector image
wksp = LoadISISNexus('INTER00066223')
z = wksp.extractY()
plotly_fig = px.imshow(np.log(z), aspect='auto', origin='lower', color_continuous_scale='rainbow')
# plotly_fig.show()

img_bytes = plotly_fig.to_image(format="png")
encoding = b64encode(img_bytes).decode()
img_b64 = "data:image/png;base64," + encoding
pfig = html.Img(src=img_b64, style={'height': '500px'})
plotly_fig.write_image("assets/tmp.png")

# html.Img(src=img_b64)

ssl._create_default_https_context = ssl._create_unverified_context

inst_list = ['INTER', 'OFFSPEC', 'POLREF', 'SURF']
df = {}

for inst in inst_list:
    url = f'https://data.isis.rl.ac.uk/journals/ndx{inst.lower()}/summary.txt'
    auth_user = "ktd43279"  # input("Username: ")
    auth_passwd = "?tv6yn{kd3"

    passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, auth_user, auth_passwd)
    authhandler = urllib.request.HTTPBasicAuthHandler(passman)
    opener = urllib.request.build_opener(authhandler)

    urllib.request.install_opener(opener)
    res = urllib.request.urlopen(url)
    res_body = res.read()
    runs = res_body.decode('latin-1')  # .split('\n')
    colspecs = [(0, 8), (8, 28), (28, 52), (52, 63), (64, 72), (72, 80), (80, 89)]
    col_names = ["Run Number", "Users", "Title", "Date", "Time", "uAmps", "RB Number"]
    df[inst.upper()] = pd.read_fwf(StringIO(runs), skiprows=40000, colspecs=colspecs, names=col_names)
    df[inst.upper()]['Run Number'] = df[inst.upper()]['Run Number'].str[3:]

app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE])  # JOURNAL is also good

app.layout = dbc.Container([
    # dcc.Interval(
    #     id='interval-component',
    #     interval=6000000 * 1000,  # in milliseconds
    #     n_intervals=0,
    #     max_intervals=0
    # ),
    html.Div(id='hidden-div', style={'display': 'none'}),
    html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(html.Div([dcc.Dropdown(options=[{'label': i, 'value': i} for i in inst_list],
                                                   value='INTER', id='inst-selector',
                                                   multi=False,
                                                   persistence=True,
                                                   persistence_type='session'
                                                   )]), width=3),

                    dbc.Col(html.Div([dcc.Dropdown(options=[{'label': i, 'value': i}
                                                            for i in np.sort(df['INTER']['RB Number'].unique())[::-1]],
                                                   id='rb-selector',
                                                   multi=False,
                                                   persistence=True,
                                                   persistence_type='session'
                                                   )]), width=3),
                ]
            ),
            dbc.Row(html.Br()),
            dbc.Row([
                dbc.Col([
                    dbc.Input(
                        id="file-path",
                        type="text",
                        placeholder="",
                        # autoComplete="off"  # Disable auto-completion
                        style={'width': '400px', 'display': 'table-cell', 'padding': 5,
                               'verticalAlign': 'middle', 'marginLeft': 0},
                    ),
                    ],),
                dbc.Col(html.Div([dbc.Button("Generate detector images", id="image-button", color="primary", size="sm"), ]))
            ]),
            dbc.Row(
                dbc.Col([
                    dash_table.DataTable(
                        id='datatable-journal',
                        data=df['INTER'].to_dict('records'),
                        columns=[{"name": i, "id": i, 'editable': False} for i in df['INTER'].columns] +
                                [{'id': 'Comments', 'name': 'Comments'}],
                        editable=True,
                        filter_action="native",
                        sort_action="native",
                        sort_mode="multi",
                        page_action="native",
                        style_table={'width': '100%', 'margin': 'auto'},  # Adjust the width as needed
                        style_data={
                            'color': 'black',
                            'backgroundColor': 'white'
                        },
                        style_cell={'padding-right': '10px',
                                    'padding-left': '10px',
                                    'font_size': '12px',
                                    },
                        style_cell_conditional=[
                            {'if': {'column_id': 'Run number'},
                             'width': '50'},
                            # {'if': {'column_id': 'Region'},
                            #  'width': '30%'},
                        ],
                        tooltip_data=[
                            {
                                'Run Number': {
                                    'value': f'Detector image\n\n![Image](/assets/tmp.png)',
                                    'type': 'markdown'
                                }
                            }, ],
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(220, 220, 220)',
                                # 'fontSize': '8'
                            }
                        ],
                        style_header={
                            'backgroundColor': 'rgb(210, 210, 210)',
                            'color': 'black',
                            'fontWeight': 'bold',
                            'fontSize': '10',
                            'textAlign': 'left'
                        },
                        tooltip_duration=None
                    ),
                ], width=6)
            ),
        ]
    )
])

@callback(
    Output('datatable-journal', 'tooltip_data'),
    Input('inst-selector', 'value'),
    Input('datatable-journal', 'data')
)
def generate_images(inst, selected_runs):
    tooltips = []
    for run in selected_runs:
        fname = os.path.join(os.getcwd(), "assets", str(run['Run Number']) + ".png")
        print(fname)
        if not os.path.isfile(fname):
            # wksp = LoadISISNexus(inst + str(run['Run Number']))
            wksp = LoadRaw(Filename=inst + "000" + str(run['Run Number']+'.raw'), LoadLogFiles=False,
                           LoadMonitors='Exclude', OutputWorkspace='tmp')
            tmp = mtd['tmp']
            z = tmp.extractY()
            plotly_fig = px.imshow(np.log(z), aspect='auto', origin='lower', color_continuous_scale='rainbow')

            img_bytes = plotly_fig.to_image(format="png")
            encoding = b64encode(img_bytes).decode()
            img_b64 = "data:image/png;base64," + encoding
            pfig = html.Img(src=img_b64, style={'height': '500px'})

            plotly_fig.write_image(fname)

        print(os.path.basename(fname))
        tooltip_content = f'Detector image for Run {run["Run Number"]}\n\n![Image](/assets/{os.path.basename(fname)})'
        tooltip_entry = {
            'Run Number': {
                'value': tooltip_content,
                'type': 'markdown'
            }
        }
        tooltips.append(tooltip_entry)

    return tooltips

    # for run in selected_runs:
    #     print(run['Run Number'])
    #     wksp = LoadISISNexus(inst+str(run['Run Number']))
    #     z = wksp.extractY()
    #     plotly_fig = px.imshow(np.log(z), aspect='auto', origin='lower', color_continuous_scale='rainbow')
    #
    #     img_bytes = plotly_fig.to_image(format="png")
    #     encoding = b64encode(img_bytes).decode()
    #     img_b64 = "data:image/png;base64," + encoding
    #     pfig = html.Img(src=img_b64, style={'height': '500px'})
    #
    #     fname = "/assets/" + str(run['Run Number']) + ".png"
    #     if not os.path.isfile(fname):
    #         plotly_fig.write_image(fname)
    #
    #     im = [
    #                             {
    #                                 'Run Number': {
    #                                     'value': f'Detector image\n\n![Image]({fname})',
    #                                     'type': 'markdown'
    #                                 }
    #                             }, ]
    # return im


@callback(
    Output('datatable-journal', 'data'),
    Output('rb-selector', 'options'),
    # Output('datatable-journal', 'tooltip_data'),
    Input('inst-selector', 'value'),
    Input('rb-selector', 'value')
)
def select_inst(inst_selected, rb):
    button_clicked = ctx.triggered_id
    data_inst = df[inst_selected].to_dict('records')

    data = df[inst_selected][df[inst_selected]['RB Number'] == rb].to_dict('records')
    rb_list = [{'label': i, 'value': i} for i in np.sort(df[inst_selected]['RB Number'].unique())[::-1]]

    return data, rb_list


@callback(
    Output('hidden-div', 'children'),
    Input('datatable-journal', 'data'),
    State('file-path', 'value'),
    State('rb-selector', 'value')
)
def select_inst(changed_df, fname, rb):
    if fname:  # Check if fname is not None or empty
        df_out = pd.DataFrame(changed_df)  # Specify dtype as needed
        df_out.to_csv(fname.split('.')[0] + str(rb) + '.csv')
    else:
        raise PreventUpdate


if __name__ == '__main__':
    app.run(debug=True)
