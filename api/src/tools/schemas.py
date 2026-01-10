from typing import Literal
from pydantic import BaseModel, Field


class StatsParams(BaseModel):
    sql_query: str = Field(
        description="The DuckDB SQL query to execute. Must be a SELECT statement.",
        min_length=10,
    )


class PlotParams(BaseModel):
    chart_type: Literal["trend_30d", "history_12m"] = Field(
        description="The specific type of chart to generate."
    )


class SearchParams(BaseModel):
    query: str = Field(
        description="The search query for external news.", min_length=5, max_length=100
    )
