import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from api.src.agents.deps import AgentDeps

matplotlib.use("Agg")

logger = logging.getLogger(__name__)


@dataclass
class PlotTool:
    """
    Tool responsible for generating and saving visualization charts.
    """

    output_dir: Path

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def __call__(
        self,
        ctx: RunContext[AgentDeps],
        chart_type: str,
    ) -> str:
        logger.info(f"Agent requested chart: {chart_type}")
        con = ctx.deps.get_db_connection(read_only=True)

        try:
            max_date_res = con.execute(
                "SELECT MAX(DT_NOTIFIC) FROM srag_analytics"
            ).fetchone()

            if not max_date_res or not max_date_res[0]:
                return "Error: Database is empty."

            max_date = max_date_res[0]

            sns.set_theme(style="whitegrid")
            fig, ax = plt.subplots(figsize=(10, 6))

            stats_summary = ""

            if chart_type == "trend_30d":
                query = f"""
                    SELECT DT_NOTIFIC, COUNT(*) AS cases
                    FROM srag_analytics
                    WHERE DT_NOTIFIC >= CAST('{max_date}' AS DATE) - INTERVAL 45 DAY
                    GROUP BY 1 ORDER BY 1 ASC
                """
                df = con.execute(query).df()
                df["DT_NOTIFIC"] = pd.to_datetime(df["DT_NOTIFIC"])

                df = (
                    df.set_index("DT_NOTIFIC")
                    .resample("D")
                    .sum()
                    .fillna(0)
                    .reset_index()
                )

                last_7d = df.tail(7)["cases"].sum()
                prev_7d = df.iloc[-14:-7]["cases"].sum()
                growth_rate = (
                    ((last_7d - prev_7d) / prev_7d * 100) if prev_7d > 0 else 0
                )
                peak_day = df.loc[df["cases"].idxmax()]

                stats_summary = (
                    f"DATA SUMMARY FOR AGENT: Growth rate: {growth_rate:+.1f}%. "
                    f"Last 7 days total: {last_7d}. "
                    f"Peak: {peak_day['cases']} on {peak_day['DT_NOTIFIC'].strftime('%Y-%m-%d')}."
                )

                cutoff_30d = pd.to_datetime(max_date) - pd.Timedelta(days=30)
                plot_df = df[df["DT_NOTIFIC"] >= cutoff_30d]

                sns.lineplot(
                    data=plot_df,
                    x="DT_NOTIFIC",
                    y="cases",
                    marker="o",
                    color="#d62728",
                    ax=ax,
                )

                trend_icon = "📈" if growth_rate > 0 else "📉"
                ax.set_title(f"30-Day Trend | Growth: {growth_rate:+.1f}% {trend_icon}")
                ax.tick_params(axis="x", rotation=45)

            elif chart_type == "history_12m":
                query = f"""
                    SELECT strftime(DT_NOTIFIC, '%Y-%m') AS month_str, COUNT(*) AS cases
                    FROM srag_analytics
                    WHERE DT_NOTIFIC >= CAST('{max_date}' AS DATE) - INTERVAL 12 MONTH
                    GROUP BY 1 ORDER BY 1 ASC
                """
                df = con.execute(query).df()

                total_cases = df["cases"].sum()
                peak_month = df.loc[df["cases"].idxmax()]
                avg_cases = df["cases"].mean()

                stats_summary = (
                    f"DATA SUMMARY FOR AGENT: 12 months total: {total_cases}. "
                    f"Avg: {avg_cases:.1f}. Peak: {peak_month['month_str']}."
                )

                sns.barplot(data=df, x="month_str", y="cases", color="#1f77b4", ax=ax)
                ax.set_title("12-Month History")
                ax.tick_params(axis="x", rotation=45)

            fig.tight_layout()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{chart_type}_{timestamp}.png"
            filepath = self.output_dir / filename

            fig.savefig(
                filepath, format="png", dpi=100, facecolor="white", bbox_inches="tight"
            )

            plt.close(fig)

            logger.info(f"Plot saved to {filepath}")
            return f"**System Note:** Chart generated at {filepath}.\n\n{stats_summary}"

        except Exception as e:
            logger.error(f"Plot generation failed: {e}", exc_info=True)

            if "fig" in locals():
                plt.close(fig)

            return f"Error generating chart: {str(e)}"

        finally:
            con.close()


def create_plot_tool(output_dir: Path) -> Tool[AgentDeps]:
    """
    Factory to create the Plot Tool with a configured output directory.
    """
    return Tool(
        PlotTool(output_dir=output_dir).__call__,
        name="plot_tool",
        description=(
            "Generates a chart and saves it to disk. "
            "Returns a statistical summary to help interpret the visual data."
        ),
    )
