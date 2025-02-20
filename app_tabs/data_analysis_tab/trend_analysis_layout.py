import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc

from utils import dash_dynamic_components as ddc, dash_persistence
from utils.charts import empty_figure
from utils.graph_with_horizontal_selection_AIO import GraphWithHorizontalSelectionAIO
from . import common_layout
from app_tabs.common.layout import GRAPH_CONFIG, NON_INTERACTIVE_GRAPH_CONFIG


TREND_ANALYSIS_METHOD_RADIO_ID = 'trend-analysis-method-radio'
TREND_GRAPH_ID = 'trend-analysis-graph'
AUTOCORRELATION_GRAPH_ID = 'autocorrelation-graph'
TREND_SUMMARY_BAR_GRAPH_ID = 'trend-summary-bar-graph'
TREND_ALIGN_ALL_Y_AXES_BUTTON_ID = 'trend-analysis-align-all-y-axes-button'

# TREND_SUMMARY_CONTAINER_ID = 'trend-summary-container'

LINEAR_FIT_METHOD = 'Linear fit method'
NON_PARAMETRIC_MANN_KENDALL = 'Non-parametric Mann-Kendall'
THEIL_SEN_SLOPE_ESTIMATE = 'Theil-Sen slope estimate'
TREND_ANALYSIS_METHODS = [
    LINEAR_FIT_METHOD,
    NON_PARAMETRIC_MANN_KENDALL,
    THEIL_SEN_SLOPE_ESTIMATE,
]

AGGREGATE_CHECKBOX_ID = 'trend-analysis-aggregate-checkbox'
AGGREGATE_COLLAPSE_ID = 'trend-analysis-aggregate-collapse'
AGGREGATION_PERIOD_SELECT_ID = 'trend-analysis-aggregation-period-select'
AGGREGATION_PERIOD_WORDINGS = {
    'D': ('day', 'daily'),
    'W': ('week', 'weekly'),
    'M': ('month', 'monthly'),
    'Q': ('season', 'seasonal'),
    'Y': ('year', 'yearly'),
}
AGGREGATION_PERIOD_TIMEDELTA = {
    'D': pd.Timedelta(1, 'D').to_timedelta64(),
    'W': pd.Timedelta(7, 'D').to_timedelta64(),
    'M': pd.Timedelta(31, 'D').to_timedelta64(),
    'Q': pd.Timedelta(92, 'D').to_timedelta64(),
    'Y': pd.Timedelta(365, 'D').to_timedelta64(),
}
DEFAULT_AGGREGATION_PERIOD = 'M'

AGGREGATION_FUNCTION_SELECT_ID = 'trend-analysis-aggregation-function-select'
AGGREGATION_FUNCTIONS = {
    'mean': lambda resampled_series: resampled_series.mean(),
    'median': lambda resampled_series: resampled_series.median(),
}
DEFAULT_AGGREGATION_FUNCTION = 'mean'

DESEASONIZE_CHECKBOX_ID = 'trend-analysis-deseasonize-checkbox'
APPLY_MOVING_AVERAGE_COLLAPSE_ID = 'trend-analysis-deseasonize-collapse'
APPLY_MOVING_AVERAGE_CHECKBOX_ID = 'apply-moving-average-checkbox'
MOVING_AVERAGE_PERIOD_SELECT_ID = 'trend-analysis-moving_average-period-select'

SHOW_GRAPHS_CHECKLIST_ID = 'trend-analysis-show-graphs-checklist'

TREND_ANALYSIS_AIO_ID = 'trend_analysis_time_filter'
TREND_ANALYSIS_AIO_CLASS = 'trend_analysis'


def get_time_filter():
    time_filter = GraphWithHorizontalSelectionAIO(
        aio_id=TREND_ANALYSIS_AIO_ID,
        aio_class=TREND_ANALYSIS_AIO_CLASS,
        dynamic_component=True,
        x_axis_type='time',
        variable_label='time',
        x_label='time',
    )
    return time_filter


def get_trend_analysis_cardbody(time_filter):
    analysis_method_radio = dbc.RadioItems(
        id=ddc.add_active_to_component_id(TREND_ANALYSIS_METHOD_RADIO_ID),
        options=[
            {'label': analysis_method, 'value': analysis_method}
            for analysis_method in TREND_ANALYSIS_METHODS
        ],
        value=TREND_ANALYSIS_METHODS[0],
        inline=False,
        persistence=True,
        persistence_type='session',
    ),

    trend_analysis_method_radio = dbc.Card([
        dbc.CardHeader('Analysis method'),
        dbc.CardBody(analysis_method_radio),
    ])

    aggregate_checkbox = dbc.Checkbox(
        id=ddc.add_active_to_component_id(AGGREGATE_CHECKBOX_ID),
        label='Aggregate',
        value=False,
    )

    aggregation_period_select = [
        dbc.Col(dbc.Label('Aggregation period:'), width=6),
        dbc.Col(
            dbc.Select(
                id=ddc.add_active_to_component_id(AGGREGATION_PERIOD_SELECT_ID),
                options=[
                    {'label': period_label, 'value': period_id}
                    for period_id, (period_label, _) in AGGREGATION_PERIOD_WORDINGS.items()
                ],
                value=DEFAULT_AGGREGATION_PERIOD,
                **dash_persistence.get_dash_persistence_kwargs(True)
            ),
            width=6
        )
    ]

    aggregation_function_select = [
        dbc.Col(dbc.Label('Aggregation function:'), width=6),
        dbc.Col(
            dbc.Select(
                id=ddc.add_active_to_component_id(AGGREGATION_FUNCTION_SELECT_ID),
                options=[
                    {'label': agg_func_label, 'value': agg_func_label}
                    for agg_func_label in AGGREGATION_FUNCTIONS.keys()
                ],
                value=DEFAULT_AGGREGATION_FUNCTION,
                **dash_persistence.get_dash_persistence_kwargs(True)
            ),
            width=6
        )
    ]

    deseasonize_checkbox = dbc.Checkbox(
        id=ddc.add_active_to_component_id(DESEASONIZE_CHECKBOX_ID),
        label='Remove seasonal component',
        value=False,
    )

    apply_moving_average_checkbox = dbc.Checkbox(
        id=ddc.add_active_to_component_id(APPLY_MOVING_AVERAGE_CHECKBOX_ID),
        label='Apply moving average',
        value=False,
    )

    smoothing_period_select = [
        dbc.Col(dbc.Label('Window size'), width=6),
        dbc.Col(
            dbc.Select(
                id=ddc.add_active_to_component_id(MOVING_AVERAGE_PERIOD_SELECT_ID),
                options=[
                    {'label': period_label, 'value': period_id}
                    for period_id, (period_label, _) in AGGREGATION_PERIOD_WORDINGS.items()
                ],
                value=DEFAULT_AGGREGATION_PERIOD,
                **dash_persistence.get_dash_persistence_kwargs(True)
            ),
            width=6
        )
    ]

    trend_analysis_method_parameters_card = dbc.Card([
        dbc.CardHeader('Parameters of time series pre-processing'),
        dbc.CardBody([
            dbc.Form([
                dbc.Row(dbc.Label('Time filter:')),
                dbc.Row(time_filter.get_graph()), #, width=6, style=BORDER_STYLE),
                dbc.Row(time_filter.get_range_controller()),
                dbc.Row(aggregate_checkbox),
                dbc.Collapse(
                    dbc.Card(dbc.CardBody(
                        dbc.Form([
                            dbc.Row(aggregation_period_select),
                            dbc.Row(aggregation_function_select),
                            dbc.Row(common_layout.minimal_sample_size_input),
                        ])
                    )),
                    id=ddc.add_active_to_component_id(AGGREGATE_COLLAPSE_ID),
                    is_open=False
                ),
                dbc.Row(deseasonize_checkbox),
                dbc.Row(apply_moving_average_checkbox),
                dbc.Collapse(
                    dbc.Card(dbc.CardBody(
                        dbc.Form([
                            dbc.Row(smoothing_period_select),
                        ])
                    )),
                    id=ddc.add_active_to_component_id(APPLY_MOVING_AVERAGE_COLLAPSE_ID),
                    is_open=False
                ),
                # dbc.Row([
                #     dbc.Label('Time series to plot:'),
                #     dbc.Checklist(
                #         id=ddc.add_active_to_component_id(SHOW_GRAPHS_CHECKLIST_ID),
                #         options=[
                #             {'label': 'original ', 'value': 'orig'},
                #             {'label': 'de-seasonised', 'value': 'deseason'},
                #             {'label': 'trend', 'value': 'trend'},
                #         ],
                #         value=['orig', 'deseason', 'trend'],
                #         inline=True,
                #         **dash_persistence.get_dash_persistence_kwargs(persistence_id=True)
                #     ),
                # ]),
            ]),
        ]),
    ])

    return [
        time_filter.get_data_stores(),
        dbc.Row(common_layout.variables_checklist),
        dbc.Row(trend_analysis_method_radio),
        dbc.Row(trend_analysis_method_parameters_card),
    ]


#def get_trend_summary_container():
#    return dbc.Container(id=ddc.add_active_to_component_id(TREND_SUMMARY_CONTAINER_ID))


def _get_trend_graph():
    graph = dcc.Graph(
        id=ddc.add_active_to_component_id(TREND_GRAPH_ID),
        figure=empty_figure(),
        config=GRAPH_CONFIG,
        # style={"border": "1px grey solid"},
        # responsive=True,  # WARNING: this triggers relayoutData={'autosize': True}
    ) # does it provide any performance improvement to scattergl?, config={'plotGlPixelRatio': 1})

    # return dbc.Card([
    #     dbc.CardBody(graph),
    #     dbc.CardFooter(dbc.Row(dbc.Col(align_yaxes_button, width='auto'), justify='center'))
    # ])
    return graph


def _get_align_y_axes_button():
    align_yaxes_button = dbc.Button(
        id=ddc.add_active_to_component_id(TREND_ALIGN_ALL_Y_AXES_BUTTON_ID),
        n_clicks=0,
        outline=True,
        color='primary',
        type='submit',
        style={'font-weight': 'bold'},
        size='lg',
        children='Align y-axes',
    )
    return align_yaxes_button


def _get_autocorrelation_graph():
    graph = dcc.Graph(
        id=ddc.add_active_to_component_id(AUTOCORRELATION_GRAPH_ID),
        figure=empty_figure(),
        config=NON_INTERACTIVE_GRAPH_CONFIG,
        # style={"border": "1px grey solid"},
        # responsive=True,  # WARNING: this triggers relayoutData={'autosize': True}
    ) # does it provide any performance improvement to scattergl?, config={'plotGlPixelRatio': 1})
    return graph


def _get_trend_summary_bar_graph():
    graph = dcc.Graph(
        id=ddc.add_active_to_component_id(TREND_SUMMARY_BAR_GRAPH_ID),
        figure=empty_figure(),
        config=NON_INTERACTIVE_GRAPH_CONFIG,
        # style={"border": "1px grey solid"},
        # responsive=True,  # WARNING: this triggers relayoutData={'autosize': True}
    ) # does it provide any performance improvement to scattergl?, config={'plotGlPixelRatio': 1})
    return graph


trend_graph = _get_trend_graph()
align_y_axes_button = _get_align_y_axes_button()
autocorrelation_graph = _get_autocorrelation_graph()
trend_summary_bar_graph = _get_trend_summary_bar_graph()
