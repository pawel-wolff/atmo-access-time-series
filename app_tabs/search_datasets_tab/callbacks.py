import pathlib
import warnings
import numpy as np
import pandas as pd
import pkg_resources
import dash
from dash import Output, Input, State, Patch, callback

import data_access
import data_access.common
import utils.stations_map
from app_tabs.common.data import stations
from app_tabs.common.layout import SELECTED_STATIONS_STORE_ID, DATASETS_STORE_ID, APP_TABS_ID, SELECT_DATASETS_TAB_VALUE
from app_tabs.search_datasets_tab.layout import VARIABLES_CHECKLIST_ID, VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID, \
    std_variables, SEARCH_DATASETS_BUTTON_ID, LON_MIN_ID, LON_MAX_ID, LAT_MIN_ID, LAT_MAX_ID, \
    SELECTED_STATIONS_DROPDOWN_ID, STATIONS_MAP_ID, SEARCH_DATASETS_RESET_STATIONS_BUTTON_ID, \
    MAP_BACKGROUND_RADIO_ID, MAPBOX_STYLES, DATE_RANGE_PICKER_ID, MAP_ZOOM_STORE_ID
from utils.stations_map import DEFAULT_STATIONS_SIZE, SELECTED_STATIONS_OPACITY, UNSELECTED_STATIONS_OPACITY, \
    SELECTED_STATIONS_SIZE, UNSELECTED_STATIONS_SIZE
from utils.charts import CATEGORY_ORDER, COLOR_BY_CATEGORY
from log import logger, log_exception, log_exectime
from data_processing.utils import points_inside_polygons
from utils.helper import all_is_None
from utils.exception_handler import callback_with_exc_handling, AppException, AppWarning


@callback_with_exc_handling(
    Output(VARIABLES_CHECKLIST_ID, 'value'),
    Input(VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID, 'value'),
    prevent_initial_call=True,
)
@log_exception
def toogle_variable_checklist(variables_checklist_all_none_switch):
    if variables_checklist_all_none_switch:
        return std_variables['value'].tolist()
    else:
        return []


@callback_with_exc_handling(
    Output(SEARCH_DATASETS_BUTTON_ID, 'disabled'),
    Input(SELECTED_STATIONS_STORE_ID, 'data'),
    Input(VARIABLES_CHECKLIST_ID, 'value'),
)
@log_exception
def search_datasets_button_disabled(selected_stations_idx, selected_variables):
    return not (selected_stations_idx and selected_variables)


@callback_with_exc_handling(
    Output(STATIONS_MAP_ID, 'figure', allow_duplicate=True),
    Input(MAP_BACKGROUND_RADIO_ID, 'value'),
    prevent_initial_call=True
)
@log_exception
def change_map_background(map_background):
    if map_background not in MAPBOX_STYLES:
        raise dash.exceptions.PreventUpdate
    patched_fig = Patch()
    patched_fig['layout']['mapbox']['style'] = map_background
    return patched_fig


@callback_with_exc_handling(
    Output(DATASETS_STORE_ID, 'data'),
    Output(APP_TABS_ID, 'value', allow_duplicate=True),
    Input(SEARCH_DATASETS_BUTTON_ID, 'n_clicks'),
    State(VARIABLES_CHECKLIST_ID, 'value'),
    State(SELECTED_STATIONS_STORE_ID, 'data'),
    State(DATE_RANGE_PICKER_ID, 'start_date'),
    State(DATE_RANGE_PICKER_ID, 'end_date'),
    prevent_initial_call=True
)
@log_exception
#@log_exectime
def search_datasets(n_clicks, selected_variables, selected_stations_idx, start_date, end_date):
    if not (selected_stations_idx and selected_variables):
        raise dash.exceptions.PreventUpdate

    empty_datasets_df = pd.DataFrame(
        columns=[
            'title', 'url', 'ecv_variables', 'platform_id', 'RI', 'var_codes', 'ecv_variables_filtered',
            'std_ecv_variables_filtered', 'var_codes_filtered', 'time_period_start', 'time_period_end',
            'platform_id_RI', 'id'
        ]
    )   # TODO: do it cleanly

    lon_min, lon_max, lat_min, lat_max = _get_bounding_box(selected_stations_idx)

    datasets_df = data_access.get_datasets(selected_variables, lon_min, lon_max, lat_min, lat_max)

    if datasets_df is None:
        datasets_df = empty_datasets_df

    selected_stations = stations.iloc[selected_stations_idx]
    datasets_df_filtered = datasets_df[
        datasets_df['platform_id'].isin(selected_stations['short_name']) &
        datasets_df['RI'].isin(selected_stations['RI'])     # short_name of the station might not be unique among RI's
    ]

    # filter on date range
    date_range_filter = True
    if start_date is not None:
        date_range_filter &= datasets_df_filtered['time_period_end'] > start_date
    if end_date is not None:
        date_range_filter &= datasets_df_filtered['time_period_start'] < end_date
    # temporary patch, until error handling will be done
    if False and date_range_filter is not True:
        datasets_df_filtered = datasets_df_filtered[date_range_filter]

    datasets_df_filtered = datasets_df_filtered.reset_index(drop=True)
    datasets_df_filtered['id'] = datasets_df_filtered.index

    if len(datasets_df_filtered) > 0:
        new_tab = SELECT_DATASETS_TAB_VALUE
    else:
        new_tab = dash.no_update
        warnings.warn('No datasets found. Change search criteria.', category=AppWarning)

    return datasets_df_filtered.to_json(orient='split', date_format='iso'), new_tab


def _get_selected_points(selected_stations):
    if selected_stations is not None:
        points = selected_stations['points']
        for point in points:
            point['idx'] = round(point['customdata'][0])
    else:
        points = []
    return pd.DataFrame.from_records(points, index='idx', columns=['idx', 'lon', 'lat'])


def _get_bounding_box(s):
    selected_points_df = stations.loc[s]

    # decimal precision for bounding box coordinates (lon/lat)
    decimal_precision = 1

    lon_min, lon_max, lat_min, lat_max = np.inf, -np.inf, np.inf, -np.inf

    if len(selected_points_df) > 0:
        # find bounding box for selected points
        # epsilon = np.power(10., -decimal_precision)  # precision margin for filtering on lon/lat of stations later on
        epsilon = 0
        lon_min2, lon_max2 = selected_points_df['longitude'].min() - epsilon, selected_points_df['longitude'].max() + epsilon
        lat_min2, lat_max2 = selected_points_df['latitude'].min() - epsilon, selected_points_df['latitude'].max() + epsilon

        # find a common bounding box for the both bboxes found above
        lon_min, lon_max = np.min((lon_min, lon_min2)), np.max((lon_max, lon_max2))
        lat_min, lat_max = np.min((lat_min, lat_min2)), np.max((lat_max, lat_max2))

    if not np.all(np.isfinite([lon_min, lon_max, lat_min, lat_max])):
        return [None] * 4
    # return [round(coord, decimal_precision) for coord in (lon_min, lon_max, lat_min, lat_max)]
    epsilon = np.power(10., -decimal_precision)
    magnitude = np.power(10., decimal_precision)
    return \
        np.floor(lon_min * magnitude) * epsilon, \
        np.ceil(lon_max * magnitude) * epsilon, \
        np.floor(lat_min * magnitude) * epsilon, \
        np.ceil(lat_max * magnitude) * epsilon,


def _get_selected_stations_dropdown(selected_stations_df, stations_dropdown_options):
    df = selected_stations_df
    labels = df['short_name'] + ' (' + df['long_name'] + ', ' + df['RI'] + ')'
    values = labels.index.to_list()
    options = labels.to_dict()
    if stations_dropdown_options is not None:
        existing_options = {opt['value']: opt['label'] for opt in stations_dropdown_options}
        options.update(existing_options)
    options = [{'value': value, 'label': label} for value, label in options.items()]
    return options, values
    # options = labels.rename('label').reset_index().rename(columns={'index': 'value'})
    # return options.to_dict(orient='records'), list(options['value'])


@callback_with_exc_handling(
    Output(SELECTED_STATIONS_STORE_ID, 'data'),
    Output(STATIONS_MAP_ID, 'figure'),
    Output(MAP_ZOOM_STORE_ID, 'data'),
    Output(SELECTED_STATIONS_DROPDOWN_ID, 'options'),
    Output(SELECTED_STATIONS_DROPDOWN_ID, 'value'),
    Output(LON_MIN_ID, 'value'),
    Output(LON_MAX_ID, 'value'),
    Output(LAT_MIN_ID, 'value'),
    Output(LAT_MAX_ID, 'value'),
    Input(SEARCH_DATASETS_RESET_STATIONS_BUTTON_ID, 'n_clicks'),
    Input(STATIONS_MAP_ID, 'selectedData'),
    Input(STATIONS_MAP_ID, 'clickData'),
    Input(STATIONS_MAP_ID, 'relayoutData'),
    Input(SELECTED_STATIONS_DROPDOWN_ID, 'value'),
    Input(LON_MIN_ID, 'value'),
    Input(LON_MAX_ID, 'value'),
    Input(LAT_MIN_ID, 'value'),
    Input(LAT_MAX_ID, 'value'),
    State(MAP_ZOOM_STORE_ID, 'data'),
    State(SELECTED_STATIONS_STORE_ID, 'data'),
    State(SELECTED_STATIONS_DROPDOWN_ID, 'options'),
)
@log_exception
def get_selected_stations_bbox_and_dropdown(
        reset_stations_button,
        selected_data,
        click_data,
        map_relayoutData,
        stations_dropdown,
        lon_min, lon_max, lat_min, lat_max,
        previous_zoom,
        selected_stations_idx,
        stations_dropdown_options
):
    # TODO: (refactor) move stations update to utils.stations_map module
    ctx_keys = list(dash.ctx.triggered_prop_ids)
    ctx_values = list(dash.ctx.triggered_prop_ids.values())

    # apply station unclustering
    zoom = map_relayoutData.get('mapbox.zoom', previous_zoom) if isinstance(map_relayoutData, dict) else previous_zoom
    lon_3857_displaced, lat_3857_displaced, lon_displaced, lat_displaced = utils.stations_map.uncluster(stations['lon_3857'], stations['lat_3857'], zoom)

    if SELECTED_STATIONS_DROPDOWN_ID in ctx_values and stations_dropdown is not None:
        selected_stations_idx = sorted(stations_dropdown)

    if SEARCH_DATASETS_RESET_STATIONS_BUTTON_ID in ctx_values:
        selected_stations_idx = None
        lon_min, lon_max, lat_min, lat_max = (None,) * 4
        new_lon_min, new_lon_max, new_lat_min, new_lat_max = (None, ) * 4
    else:
        new_lon_min, new_lon_max, new_lat_min, new_lat_max = (dash.no_update, ) * 4

    if (f'{STATIONS_MAP_ID}.selectedData' in ctx_keys or f'{STATIONS_MAP_ID}.clickData' in ctx_keys)\
            and selected_data and 'points' in selected_data and len(selected_data['points']) > 0:
        if 'range' in selected_data or 'lassoPoints' in selected_data:
            currently_selected_stations_on_map_idx = [
                p['customdata'][0]
                for p in selected_data['points']
                if 'customdata' in p  # take account only traces corresponding to stations / regions
                                      # and NOT to displacement vectors or original stations' positions
            ]
            # it does not contain points from categories which were deselected on the legend
            # however might contain points that we clicked on while keeping the key 'shift' pressed
            # some of the latter might have been actually un-clicked (deselected)
            # that's why we compute stations_in_current_selection_idx (indices of stations inside the current range
            # or lasso selection, regardless their category is switched on or off)
            if 'range' in selected_data and 'mapbox' in selected_data['range']:
                mapbox_range = selected_data['range']['mapbox']
                try:
                    (lon1, lat1), (lon2, lat2) = mapbox_range
                except TypeError:
                    print(f'mapbox_range: {mapbox_range}')
                    raise dash.exceptions.PreventUpdate
                lon1, lon2 = sorted([lon1, lon2])
                lat1, lat2 = sorted([lat1, lat2])
                lon = stations['longitude']
                lat = stations['latitude']
                stations_in_current_selection_idx = stations[(lon >= lon1) & (lon <= lon2) & (lat >= lat1) & (lat <= lat2)].index
            elif 'lassoPoints' in selected_data and 'mapbox' in selected_data['lassoPoints']:
                mapbox_lassoPoints = selected_data['lassoPoints']['mapbox']
                mapbox_lassoPoints = np.array(mapbox_lassoPoints).T
                points = np.array([stations['longitude'].values, stations['latitude'].values])
                stations_in_current_selection_idx, = np.nonzero(points_inside_polygons(points, mapbox_lassoPoints))
            else:
                stations_in_current_selection_idx = []
            stations_in_current_selection_idx = set(stations_in_current_selection_idx).intersection(currently_selected_stations_on_map_idx)
            # we take the intersection because some categories might be switched off on the legend

            selected_stations_idx = sorted(set(selected_stations_idx if selected_stations_idx is not None else []).union(stations_in_current_selection_idx))
        elif click_data and 'points' in click_data:
            currently_selected_stations_on_map_idx = [p['customdata'][0] for p in click_data['points']]
            selected_stations_idx = sorted(set(selected_stations_idx if selected_stations_idx is not None else []).symmetric_difference(currently_selected_stations_on_map_idx))

    if {LON_MIN_ID, LON_MAX_ID, LAT_MIN_ID, LAT_MAX_ID}.isdisjoint(ctx_values):
        # the callback was not fired by user's input on bbox, so we possibly enlarge the bbox to fit all selected stations
        if selected_stations_idx is not None and len(selected_stations_idx) > 0:
            stations_lon_min, stations_lon_max, stations_lat_min, stations_lat_max = _get_bounding_box(selected_stations_idx)
            if lon_min is not None and stations_lon_min < lon_min:
                new_lon_min = stations_lon_min
            if lon_max is not None and stations_lon_max > lon_max:
                new_lon_max = stations_lon_max
            if lat_min is not None and stations_lat_min < lat_min:
                new_lat_min = stations_lat_min
            if lat_max is not None and stations_lat_max > lat_max:
                new_lat_max = stations_lat_max
    elif not all_is_None(lon_min, lon_max, lat_min, lat_max):
        # the callback was fired by user's input to bbox, and bbox is not all None
        # so we apply restriction of selected stations to the bbox
        selected_stations_df = stations.loc[selected_stations_idx] if selected_stations_idx is not None else stations
        lon = selected_stations_df['longitude']
        lat = selected_stations_df['latitude']
        bbox_cond = True
        if lon_min is not None:
            bbox_cond = bbox_cond & (lon >= lon_min)
        if lon_max is not None:
            bbox_cond = bbox_cond & (lon <= lon_max)
        if lat_min is not None:
            bbox_cond = bbox_cond & (lat >= lat_min)
        if lat_max is not None:
            bbox_cond = bbox_cond & (lat <= lat_max)
        selected_stations_idx = sorted(bbox_cond[bbox_cond].index)

    size = pd.Series(UNSELECTED_STATIONS_SIZE, index=stations.index)
    opacity = pd.Series(UNSELECTED_STATIONS_OPACITY, index=stations.index)

    # this change is OK since we are going to delete bounding box feature
    # if selected_stations_idx is not None:
    if selected_stations_idx:
        opacity.loc[selected_stations_idx] = SELECTED_STATIONS_OPACITY
        size.loc[selected_stations_idx] = SELECTED_STATIONS_SIZE
    else:
        opacity.loc[:] = SELECTED_STATIONS_OPACITY
        size.loc[:] = DEFAULT_STATIONS_SIZE

    patched_fig = utils.stations_map.get_stations_map_patch(zoom, size, opacity)

    selected_stations_df = stations.loc[selected_stations_idx] if selected_stations_idx is not None else stations.loc[[]]
    selected_stations_dropdown_options, selected_stations_dropdown_value = _get_selected_stations_dropdown(selected_stations_df, stations_dropdown_options)

    return (
        selected_stations_idx, patched_fig, zoom,
        selected_stations_dropdown_options, selected_stations_dropdown_value,
        new_lon_min, new_lon_max, new_lat_min, new_lat_max,
    )
