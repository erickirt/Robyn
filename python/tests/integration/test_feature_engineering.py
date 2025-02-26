import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from robyn.data.entities.mmmdata import MMMData
from robyn.data.entities.holidays_data import HolidaysData
from robyn.data.entities.hyperparameters import Hyperparameters, ChannelHyperparameters
from robyn.data.entities.enums import AdstockType, DependentVarType
from robyn.modeling.feature_engineering import FeatureEngineering


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    dates = pd.date_range(start="2020-01-01", end="2022-12-31", freq="W-MON")
    n_rows = len(dates)

    return pd.DataFrame(
        {
            "DATE": dates,
            "revenue": np.random.uniform(1000, 5000, n_rows),
            "tv_S": np.random.uniform(100, 1000, n_rows),
            "facebook_S": np.random.uniform(100, 1000, n_rows),
            "custom_context": np.random.uniform(10, 100, n_rows),
            "newsletter": np.random.uniform(0, 100, n_rows),
        }
    )


@pytest.fixture
def sample_holidays():
    """Create sample holidays data for testing."""
    return pd.DataFrame(
        {
            "ds": pd.date_range(start="2020-01-01", end="2022-12-31", freq="M"),
            "holiday": "test_holiday",
            "country": "US",
            "year": [
                d.year
                for d in pd.date_range(start="2020-01-01", end="2022-12-31", freq="M")
            ],
        }
    )


@pytest.fixture
def basic_mmm_data(sample_data):
    """Create basic MMM data specification."""
    mmm_data_spec = MMMData.MMMDataSpec(
        dep_var="revenue",
        dep_var_type="revenue",
        date_var="DATE",
        context_vars=["custom_context"],
        paid_media_spends=["tv_S", "facebook_S"],
        paid_media_vars=["tv_S", "facebook_S"],
        organic_vars=["newsletter"],
        window_start=pd.Timestamp("2020-01-01"),  # Convert to Timestamp
        window_end=pd.Timestamp("2022-12-31"),  # Convert to Timestamp
    )
    return MMMData(data=sample_data, mmmdata_spec=mmm_data_spec)


@pytest.fixture
def basic_holidays_data(sample_holidays):
    """Create basic holidays data specification."""
    return HolidaysData(
        dt_holidays=sample_holidays,
        prophet_vars=[
            "trend",
            "season",
            "holiday",
        ],  # These are the variables we're testing
        prophet_country="US",
        prophet_signs=["default", "default", "default"],
    )


@pytest.fixture
def basic_hyperparameters():
    """Create basic hyperparameters configuration."""
    return Hyperparameters(
        hyperparameters={
            "tv_S": ChannelHyperparameters(
                alphas=[0.5, 3],
                gammas=[0.3, 1],
                thetas=[0.3, 0.8],
            ),
            "facebook_S": ChannelHyperparameters(
                alphas=[0.5, 3],
                gammas=[0.3, 1],
                thetas=[0, 0.3],
            ),
            "newsletter": ChannelHyperparameters(
                alphas=[0.5, 3],
                gammas=[0.3, 1],
                thetas=[0.1, 0.4],
            ),
        },
        adstock=AdstockType.GEOMETRIC,
        lambda_=[0, 1],
        train_size=[0.5, 0.8],
    )


def test_feature_engineering_initialization(
    basic_mmm_data, basic_holidays_data, basic_hyperparameters
):
    """Test if FeatureEngineering initializes correctly."""
    fe = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=basic_holidays_data,
    )
    assert fe.mmm_data == basic_mmm_data
    assert fe.hyperparameters == basic_hyperparameters
    assert fe.holidays_data == basic_holidays_data


def test_prepare_data_with_custom_context(
    basic_mmm_data, basic_holidays_data, basic_hyperparameters
):
    """Test if _prepare_data handles custom context variables correctly."""
    fe = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=basic_holidays_data,
    )

    dt_transform = fe._prepare_data()

    # Check if all expected columns exist
    assert "ds" in dt_transform.columns
    assert "dep_var" in dt_transform.columns
    assert "custom_context" in dt_transform.columns

    # Check if date transformation worked correctly
    assert pd.api.types.is_datetime64_any_dtype(pd.to_datetime(dt_transform["ds"]))


def test_feature_engineering_with_different_context_vars(
    sample_data, basic_holidays_data, basic_hyperparameters
):
    """Test if feature engineering works with different context variables."""
    mmm_data_spec = MMMData.MMMDataSpec(
        dep_var="revenue",
        dep_var_type="revenue",
        date_var="DATE",
        context_vars=["custom_context"],
        paid_media_spends=["tv_S", "facebook_S"],
        paid_media_vars=["tv_S", "facebook_S"],
        organic_vars=["newsletter"],
        window_start=pd.Timestamp("2020-01-01"),
        window_end=pd.Timestamp("2022-12-31"),
    )

    mmm_data = MMMData(data=sample_data, mmmdata_spec=mmm_data_spec)
    fe = FeatureEngineering(
        mmm_data=mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=basic_holidays_data,  # Use the fixture
    )

    result = fe.perform_feature_engineering()
    assert isinstance(result.dt_mod, pd.DataFrame)
    assert "custom_context" in result.dt_mod.columns


def test_feature_engineering_no_context_vars(
    sample_data, basic_holidays_data, basic_hyperparameters
):
    """Test if feature engineering works without context variables."""
    mmm_data_spec = MMMData.MMMDataSpec(
        dep_var="revenue",
        dep_var_type="revenue",
        date_var="DATE",
        context_vars=[],
        paid_media_spends=["tv_S", "facebook_S"],
        paid_media_vars=["tv_S", "facebook_S"],
        organic_vars=["newsletter"],
        window_start=pd.Timestamp("2020-01-01"),
        window_end=pd.Timestamp("2022-12-31"),
    )

    mmm_data = MMMData(data=sample_data, mmmdata_spec=mmm_data_spec)
    fe = FeatureEngineering(
        mmm_data=mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=basic_holidays_data,  # Use the fixture
    )

    result = fe.perform_feature_engineering()
    assert isinstance(result.dt_mod, pd.DataFrame)


def test_invalid_context_var(sample_data, basic_holidays_data, basic_hyperparameters):
    """Test handling of invalid context variables."""
    mmm_data_spec = MMMData.MMMDataSpec(
        dep_var="revenue",
        dep_var_type="revenue",
        date_var="DATE",
        context_vars=["nonexistent_var"],
        paid_media_spends=["tv_S", "facebook_S"],
        paid_media_vars=["tv_S", "facebook_S"],
        organic_vars=["newsletter"],
        window_start=pd.Timestamp("2020-01-01"),
        window_end=pd.Timestamp("2022-12-31"),
    )

    mmm_data = MMMData(data=sample_data, mmmdata_spec=mmm_data_spec)

    with pytest.raises(KeyError):
        fe = FeatureEngineering(
            mmm_data=mmm_data,
            hyperparameters=basic_hyperparameters,
            holidays_data=basic_holidays_data,  # Use the fixture
        )
        fe.perform_feature_engineering()


def test_feature_engineering_with_prophet_disabled(
    basic_mmm_data, basic_hyperparameters
):
    """Test if feature engineering works correctly when Prophet is disabled."""
    # Initialize FeatureEngineering without holidays_data
    fe = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=None,  # Explicitly disable Prophet
    )

    # Run feature engineering
    result = fe.perform_feature_engineering()

    # Check that Prophet variables are not in the output
    prophet_vars = ["trend", "season", "holiday", "monthly", "weekday"]
    for var in prophet_vars:
        assert var not in result.dt_mod.columns
        assert var not in result.dt_modRollWind.columns


def test_feature_engineering_with_empty_prophet_vars(
    basic_mmm_data, basic_hyperparameters, basic_holidays_data
):
    """Test if feature engineering works when prophet_vars is empty."""
    # Modify holidays_data to have empty prophet_vars
    holidays_data_empty = HolidaysData(
        dt_holidays=basic_holidays_data.dt_holidays,
        prophet_vars=[],
        prophet_country="US",
        prophet_signs=[],
    )

    fe = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=holidays_data_empty,
    )

    result = fe.perform_feature_engineering()

    # Check that Prophet variables are not in the output
    prophet_vars = ["trend", "season", "holiday", "monthly", "weekday"]
    for var in prophet_vars:
        assert var not in result.dt_mod.columns
        assert var not in result.dt_modRollWind.columns


def test_prophet_enable_disable_comparison(
    basic_mmm_data, basic_hyperparameters, basic_holidays_data
):
    """Test and compare results with Prophet enabled vs disabled."""
    # Run with Prophet enabled
    fe_enabled = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=basic_holidays_data,
    )
    result_enabled = fe_enabled.perform_feature_engineering()

    # Run with Prophet disabled
    fe_disabled = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=None,
    )
    result_disabled = fe_disabled.perform_feature_engineering()

    # Compare results
    assert len(result_enabled.dt_mod.columns) > len(result_disabled.dt_mod.columns)

    # Core columns should be present in both
    core_cols = ["ds", "dep_var", "tv_S", "facebook_S", "custom_context", "newsletter"]
    for col in core_cols:
        assert col in result_enabled.dt_mod.columns
        assert col in result_disabled.dt_mod.columns

    # Prophet columns should only be in enabled result
    prophet_vars = basic_holidays_data.prophet_vars
    for var in prophet_vars:
        assert var in result_enabled.dt_mod.columns
        assert var not in result_disabled.dt_mod.columns


def test_feature_engineering_with_prophet_enabled(
    basic_mmm_data, basic_hyperparameters, basic_holidays_data
):
    """Test if feature engineering works correctly when Prophet is enabled."""
    fe = FeatureEngineering(
        mmm_data=basic_mmm_data,
        hyperparameters=basic_hyperparameters,
        holidays_data=basic_holidays_data,
    )

    result = fe.perform_feature_engineering()

    # Check that specified Prophet variables are in the output
    prophet_vars = basic_holidays_data.prophet_vars
    for var in prophet_vars:
        assert var in result.dt_mod.columns
        assert var in result.dt_modRollWind.columns
