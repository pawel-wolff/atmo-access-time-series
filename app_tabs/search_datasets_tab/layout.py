import datetime

import dash_bootstrap_components as dbc
from dash import dcc, html
from plotly import express as px, graph_objects as go
import plotly.colors

import data_access
from app_tabs.common.data import stations
from utils.charts import ACTRIS_COLOR_HEX, IAGOS_COLOR_HEX, ICOS_COLOR_HEX, rgb_to_rgba

VARIABLES_CHECKLIST_ID = 'variables-checklist'

STATIONS_MAP_ID = 'stations-map'
# 'selectedData' contains a dictionary
# {
#   'point' ->
#       list of dicionaries {'pointIndex' -> index of a station in the global dataframe stations, 'lon' -> float, 'lat' -> float, ...},
#   'range' (present only if a box was selected on the map) ->
#       {'mapbox' -> [[lon_min, lat_max], [lon_max, lat_min]]}
# }

LAT_MAX_ID = 'lat-max'
LAT_MIN_ID = 'lat-min'
LON_MAX_ID = 'lon-max'
LON_MIN_ID = 'lon-min'
# 'value' contains a number (or None)

SEARCH_DATASETS_TAB_VALUE = 'search-datasets-tab'
VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID = 'variables-checklist-all-none-switch'

SELECTED_STATIONS_DROPDOWN_ID = 'selected-stations-dropdown'
# 'options' contains a list of dictionaries {'label' -> station label, 'value' -> index of the station in the global dataframe stations (see below)}
# 'value' contains a list of indices of stations selected using the dropdown

SEARCH_DATASETS_BUTTON_ID = 'search-datasets-button'
# 'n_click' contains a number of clicks at the button


def _get_std_variables(variables):
    std_vars = variables[['std_ECV_name', 'code']].drop_duplicates()
    # TODO: temporary
    try:
        std_vars = std_vars[std_vars['std_ECV_name'] != 'Aerosol Optical Properties']
    except ValueError:
        pass
    std_vars['label'] = std_vars['code'] + ' - ' + std_vars['std_ECV_name']
    return std_vars.rename(columns={'std_ECV_name': 'value'}).drop(columns='code')


variables = data_access.get_vars()
std_variables = _get_std_variables(variables)


# TODO: variable list should be loaded periodically via a callback
def get_variables_checklist():
    """
    Provide variables checklist Dash component
    See: https://dash.plotly.com/dash-core-components/checklist
    :return: dash.dcc.Checklist
    """
    variables_options = std_variables.to_dict(orient='records')
    variables_values = std_variables['value'].tolist()
    variables_checklist = dbc.Checklist(
        id=VARIABLES_CHECKLIST_ID,
        options=variables_options,
        value=variables_values,
        labelStyle={'display': 'flex'},  # display in column rather than in a row; not sure if it is the right way to do
        persistence=True,
        persistence_type='session',
    )
    return variables_checklist


# TODO: if want to move to utils.charts, need to take care about external variables: stations and STATIONS_MAP_ID
def get_stations_map():
    """
    Provide a Dash component containing a map with stations
    See: https://dash.plotly.com/dash-core-components/graph
    :return: dash.dcc.Graph object
    """
    fig = px.scatter_mapbox(
        stations,
        lat="latitude", lon="longitude", color='RI',
        hover_name="long_name",
        hover_data={
            'RI': True,
            'longitude': ':.2f',
            'latitude': ':.2f',
            'ground elevation': stations['ground_elevation'].round(0).fillna('N/A').to_list(),
            'marker_size': False
        },
        custom_data=['idx'],
        size=stations['marker_size'],
        size_max=7,
        category_orders={'RI': ['ACTRIS', 'IAGOS', 'ICOS']},
        color_discrete_sequence=[ACTRIS_COLOR_HEX, IAGOS_COLOR_HEX, ICOS_COLOR_HEX],
        zoom=2,
        # width=1200, height=700,
        center={'lon': 10, 'lat': 55},
        title='Stations map',
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={'autoexpand': True, 'r': 0, 't': 40, 'l': 0, 'b': 0},
        # width=1100, height=700,
        autosize=True,
        clickmode='event+select',
        dragmode='select',
        hoverdistance=1, hovermode='closest',  # hoverlabel=None,
    )

    regions = stations[stations['is_region']]
    regions_lon = []
    regions_lat = []
    for lon_min, lon_max, lat_min, lat_max in zip(regions['longitude_min'], regions['longitude_max'], regions['latitude_min'], regions['latitude_max']):
        if len(regions_lon) > 0:
            regions_lon.append(None)
            regions_lat.append(None)
        regions_lon.extend([lon_min, lon_min, lon_max, lon_max, lon_min])
        regions_lat.extend([lat_min, lat_max, lat_max, lat_min, lat_min])

    fig.add_trace(go.Scattermapbox(
        mode="lines",
        fill="toself",
        fillcolor=rgb_to_rgba(IAGOS_COLOR_HEX, 0.05),  # IAGOS_COLOR_HEX as rgba with opacity=0.05
        lon=regions_lon,
        lat=regions_lat,
        marker={'color': IAGOS_COLOR_HEX},
        name='IAGOS',
        legendgroup='IAGOS',
        opacity=0.3,
    ))

    # TODO: synchronize box selection on the map with max/min lon/lat input fields
    # TODO: as explained in https://dash.plotly.com/interactive-graphing (Generic Crossfilter Recipe)
    stations_map = dcc.Graph(
        id=STATIONS_MAP_ID,
        figure=fig,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'scrollZoom': True,
        }
    )
    return stations_map


def get_bbox_selection_div():
    """
    Provide a composed Dash component with input/ouput text fields which allow to provide coordinates of a bounding box
    See: https://dash.plotly.com/dash-core-components/input
    :return: dash.html.Div object
    """
    bbox_selection_div = html.Div(id='bbox-selection-div', style={'margin-top': '15px'}, children=[
        html.Div(className='row', children=[
            html.Div(className='three columns, offset-by-six columns', children=[
                dcc.Input(id=LAT_MAX_ID, style={'width': '120%'}, placeholder='lat max', type='number', min=-90, max=90),  # , step=0.01),
            ]),
        ]),
        html.Div(className='row', children=[
            html.Div(className='three columns',
                     children=html.P(children='Bounding box:', style={'width': '100%', 'font-weight': 'bold'})),
            html.Div(className='three columns',
                     children=dcc.Input(style={'width': '120%'}, id=LON_MIN_ID, placeholder='lon min', type='number',
                                        min=-180, max=180),  # , step=0.01),
                     ),
            html.Div(className='offset-by-three columns, three columns',
                     children=dcc.Input(style={'width': '120%'}, id=LON_MAX_ID, placeholder='lon max', type='number',
                                        min=-180, max=180),  # , step=0.01),
                     ),
        ]),
        html.Div(className='row', children=[
            html.Div(className='offset-by-six columns, three columns',
                     children=dcc.Input(style={'width': '120%'}, id=LAT_MIN_ID, placeholder='lat min', type='number',
                                        min=-90, max=90),  # , step=0.01),
                     ),
        ]),
    ])
    return bbox_selection_div


def get_search_datasets_tab():
    return dcc.Tab(
        label='Search datasets', value=SEARCH_DATASETS_TAB_VALUE,
        children=html.Div(style={'margin': '20px'}, children=[
            html.Div(id='search-datasets-left-panel-div', className='four columns', children=[
                html.Div(id='variables-selection-div', className='nine columns', children=[
                    html.P('Select variable(s):', style={'font-weight': 'bold'}),
                    dbc.Switch(
                        id=VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID,
                        label='Select all / none',
                        style={'margin-top': '10px'},
                        value=True,
                    ),
                    get_variables_checklist(),
                ]),

                html.Div(id='search-datasets-button-div', className='three columns',
                         children=dbc.Button(id=SEARCH_DATASETS_BUTTON_ID, n_clicks=0,
                                             color='primary',
                                             type='submit',
                                             style={'font-weight': 'bold'},
                                             children='Search datasets')),

                html.Div(id='search-datasets-left-panel-cont-div', className='twelve columns',
                         style={'margin-top': '20px'},
                         children=[
                             html.Div(children=[
                                 html.P('Date range:', style={'display': 'inline', 'font-weight': 'bold', 'margin-right': '20px'}),
                                 dcc.DatePickerRange(
                                     id='my-date-picker-range',
                                     min_date_allowed=datetime.date(1900, 1, 1),
                                     max_date_allowed=datetime.date(2022, 12, 31),
                                     initial_visible_month=datetime.date(2017, 8, 5),
                                     end_date=datetime.date(2017, 8, 25)
                                 ),
                             ]),
                             get_bbox_selection_div(),
                         ]),
            ]),

            html.Div(id='search-datasets-right-panel-div', className='eight columns', children=[
                get_stations_map(),

                html.Div(
                    id='selected-stations-div',
                    style={'margin-top': '20px'},
                    children=[
                         html.P('Selected stations (you can refine your selection)',
                                style={'font-weight': 'bold'}),
                         dcc.Dropdown(id=SELECTED_STATIONS_DROPDOWN_ID, multi=True,
                                      clearable=False),
                    ]
                ),
            ]),
        ])
    )