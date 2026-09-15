from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


# ============================================================================
# Configuration
# ============================================================================

RESULTS_ROOT = Path("results_simulations")
OUTPUT_ROOT = Path("baseline_vs_secded5_results")
REGISTER_ALIASES_FILE = Path("register_aliases.csv")

SUCCESS_STATUS = 4
TOP_N_REGISTERS = 15

USE_CASE_NAMES = {
    "buffer_overflow": "Buffer Overflow",
    "secretFunction": "Format String",
}

USE_CASE_OUTPUT_NAMES = {
    "buffer_overflow": "buffer_overflow",
    "secretFunction": "format_string",
}

FAULT_MODEL_NAMES = {
    "single_bitflip_spatial": "Single-bit / \ntwo registers",
    "multi_bitflip_reg": "Multi-bit / \none register",
    "multi_bitflip_reg_multi": "Multi-bit / \ntwo registers",
}

FAULT_MODEL_ORDER = [
    "single_bitflip_spatial",
    "multi_bitflip_reg",
    "multi_bitflip_reg_multi",
]

BASELINE_NAME = "Baseline"
SECDED5_NAME = "SECDED 5"

CONFIGURATION_ORDER = [
    BASELINE_NAME,
    SECDED5_NAME,
]

RANKING_CONFIGURATION = BASELINE_NAME
# RANKING_CONFIGURATION = SECDED5_NAME


# Metric used for the bars:
#
# "rate"  -> successful simulations / simulations targeting the register
# "count" -> raw number of successful simulations
#
METRIC = "rate"


# ============================================================================
# Data structures
# ============================================================================

@dataclass(frozen=True)
class CampaignMetadata:
    use_case: str
    protection: str
    strategy: int
    fault_model: str
    suffix: int
    folder_name: str


@dataclass
class Statistics:
    register_total: Counter[str]
    register_success: Counter[str]

    @classmethod
    def create(cls) -> "Statistics":
        return cls(
            register_total=Counter(),
            register_success=Counter(),
        )

    def merge(self, other: "Statistics") -> None:
        self.register_total.update(other.register_total)
        self.register_success.update(other.register_success)


# ============================================================================
# Campaign parsing
# ============================================================================
def parse_campaign_folder(
    folder: Path,
    use_case: str,
) -> CampaignMetadata | None:

    prefix = f"{use_case}_"

    if not folder.name.startswith(prefix):
        return None

    remaining_name = folder.name[len(prefix):]

    match = re.match(
        r"^(?P<protection>.+?)_"
        r"(?P<strategy>\d+)_"
        r"(?P<fault_model>.+)_"
        r"(?P<suffix>\d+)$",
        remaining_name,
    )

    if match is None:
        return None

    return CampaignMetadata(
        use_case=use_case,
        protection=match.group("protection"),
        strategy=int(match.group("strategy")),
        fault_model=match.group("fault_model"),
        suffix=int(match.group("suffix")),
        folder_name=folder.name,
    )


def get_configuration(
    metadata: CampaignMetadata,
) -> str | None:
    """
    Keep only:
      - baseline: wop strategy 1
      - SECDED strategy 5
    """

    protection = metadata.protection.lower()

    if protection == "wop" and metadata.strategy == 1:
        return BASELINE_NAME

    if protection == "secded" and metadata.strategy == 5:
        return SECDED5_NAME

    return None


# ============================================================================
# Register aliases
# ============================================================================
def simplify_register_name(register_path: str) -> str:
    clean_path = register_path.strip("/")

    parts = [
        part
        for part in clean_path.split("/")
        if part
    ]

    if len(parts) <= 1:
        return parts[0] if parts else clean_path

    return "/".join(parts[-2:])


def load_register_aliases(
    path: Path,
) -> dict[tuple[int, str, str], str]:

    aliases: dict[tuple[int, str, str], str] = {}

    if not path.is_file():
        raise FileNotFoundError(
            f"Alias file not found: {path.resolve()}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        expected_columns = {
            "strategy",
            "protection",
            "rtl_name",
            "logical_name",
        }

        actual_columns = set(reader.fieldnames or [])

        missing = expected_columns - actual_columns

        if missing:
            raise ValueError(
                "Missing columns in register_aliases.csv: "
                + ", ".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):

            strategy_text = row["strategy"].strip()
            protection = row["protection"].strip().lower()
            rtl_name = row["rtl_name"].strip()
            logical_name = row["logical_name"].strip()

            if not strategy_text or not protection or not rtl_name:
                print(
                    f"[Alias ignored line {line_number}] "
                    "missing strategy/protection/register."
                )
                continue

            try:
                strategy = int(strategy_text)

            except ValueError:
                print(
                    f"[Alias ignored line {line_number}] "
                    f"invalid strategy: {strategy_text}"
                )
                continue

            # Empty logical name = keep original RTL name
            if not logical_name:
                logical_name = rtl_name

            aliases[
                (
                    strategy,
                    protection,
                    rtl_name,
                )
            ] = logical_name

    return aliases


def apply_register_alias(
    rtl_name: str,
    strategy: int,
    protection: str,
    aliases: dict[tuple[int, str, str], str],
) -> str:

    key = (
        strategy,
        protection.strip().lower(),
        rtl_name,
    )

    return aliases.get(key, rtl_name)


# ============================================================================
# JSON analysis
# ============================================================================
def simulation_sort_key(
    item: tuple[str, Any],
) -> int:

    match = re.fullmatch(
        r"simulation_(\d+)",
        item[0],
    )

    if match is None:
        return -1

    return int(match.group(1))


def extract_faulted_registers(
    simulation: dict[str, Any],
    strategy: int,
    protection: str,
    aliases: dict[tuple[int, str, str], str],
) -> list[str]:

    indexed_registers: list[tuple[int, str]] = []

    def prepare(register_path: str) -> str:

        rtl_name = simplify_register_name(register_path)

        return apply_register_alias(
            rtl_name=rtl_name,
            strategy=strategy,
            protection=protection,
            aliases=aliases,
        )

    # Single register format
    single_register = simulation.get("faulted_register")

    if isinstance(single_register, str):
        indexed_registers.append(
            (
                0,
                prepare(single_register),
            )
        )

    # Multiple registers format
    pattern = re.compile(
        r"^faulted_register_(\d+)$"
    )

    for key, value in simulation.items():

        match = pattern.fullmatch(key)

        if match is None:
            continue

        if not isinstance(value, str):
            continue

        indexed_registers.append(
            (
                int(match.group(1)),
                prepare(value),
            )
        )

    indexed_registers.sort(
        key=lambda item: item[0]
    )

    # Avoid counting the same logical register twice
    # in the same simulation.
    unique_registers: list[str] = []
    seen: set[str] = set()

    for _, register in indexed_registers:

        if register in seen:
            continue

        seen.add(register)
        unique_registers.append(register)

    return unique_registers


def analyse_json_file(
    json_path: Path,
    strategy: int,
    protection: str,
    aliases: dict[tuple[int, str, str], str],
) -> Statistics:

    statistics = Statistics.create()

    try:
        with json_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            content = json.load(file)

    except (OSError, json.JSONDecodeError) as error:
        print(
            f"[Cannot read JSON] {json_path}: {error}"
        )
        return statistics

    if not isinstance(content, dict):
        return statistics

    simulations = sorted(
        (
            (key, value)
            for key, value in content.items()
            if key.startswith("simulation_")
        ),
        key=simulation_sort_key,
    )

    for simulation_name, simulation in simulations:

        # Reference simulation
        if simulation_name == "simulation_0":
            continue

        if not isinstance(simulation, dict):
            continue

        registers = extract_faulted_registers(
            simulation=simulation,
            strategy=strategy,
            protection=protection,
            aliases=aliases,
        )

        if not registers:
            continue

        is_success = (
            simulation.get("status_end")
            == SUCCESS_STATUS
        )

        for register in registers:

            statistics.register_total[register] += 1

            if is_success:
                statistics.register_success[register] += 1

    return statistics


# ============================================================================
# Complete campaign analysis
# ============================================================================
def analyse_campaigns():
    """
    stats[
        use_case
    ][
        configuration
    ][
        fault_model
    ] = Statistics
    """

    aliases = load_register_aliases(
        REGISTER_ALIASES_FILE
    )

    print(f"Aliases loaded: {len(aliases)}")
    print()

    stats = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                Statistics.create
            )
        )
    )

    for use_case in USE_CASE_NAMES:

        use_case_directory = (
            RESULTS_ROOT / use_case
        )

        if not use_case_directory.is_dir():
            print(
                f"[Missing use case] "
                f"{use_case_directory}"
            )
            continue

        for campaign_directory in sorted(
            use_case_directory.iterdir()
        ):

            if not campaign_directory.is_dir():
                continue

            metadata = parse_campaign_folder(
                campaign_directory,
                use_case,
            )

            if metadata is None:
                continue

            configuration = get_configuration(
                metadata
            )

            # Ignore all configurations except
            # baseline and SECDED strategy 5.
            if configuration is None:
                continue

            if (
                metadata.fault_model
                not in FAULT_MODEL_ORDER
            ):
                continue

            json_files = sorted(
                campaign_directory.rglob("*.json")
            )

            print(
                f"[{USE_CASE_NAMES[use_case]}] "
                f"{configuration} | "
                f"{metadata.fault_model}: "
                f"{len(json_files)} JSON files"
            )

            campaign_statistics = (
                Statistics.create()
            )

            for json_path in json_files:

                file_statistics = (
                    analyse_json_file(
                        json_path=json_path,
                        strategy=metadata.strategy,
                        protection=metadata.protection,
                        aliases=aliases,
                    )
                )

                campaign_statistics.merge(
                    file_statistics
                )

            stats[
                use_case
            ][
                configuration
            ][
                metadata.fault_model
            ].merge(
                campaign_statistics
            )

    return stats


# ============================================================================
# Metric
# ============================================================================
def get_register_value(
    statistics: Statistics,
    register: str,
) -> float | None:
    """
    Returns None when the register was not targeted
    in this campaign.

    This is important: None = N/A, NOT 0.
    """

    total = statistics.register_total.get(
        register,
        0,
    )

    if total == 0:
        return None

    successes = statistics.register_success.get(
        register,
        0,
    )

    if METRIC == "count":
        return float(successes)

    if METRIC == "rate":
        return 100.0 * successes / total

    raise ValueError(
        f"Unknown metric: {METRIC}"
    )


# ============================================================================
# Baseline ranking
# ============================================================================
def get_top_registers(
    use_case_stats,
    ranking_configuration: str,
) -> list[str]:
    """
    Select the TOP_N_REGISTERS according to one configuration.

    ranking_configuration:
        BASELINE_NAME -> most vulnerable registers before protection
        SECDED5_NAME  -> most vulnerable registers after SECDED Strategy 5

    Ranking:
        sum(successes) / sum(targeted simulations)
    across all available fault models.
    """

    total_by_register = Counter()
    success_by_register = Counter()

    for fault_model in FAULT_MODEL_ORDER:

        statistics = use_case_stats[
            ranking_configuration
        ][
            fault_model
        ]

        total_by_register.update(
            statistics.register_total
        )

        success_by_register.update(
            statistics.register_success
        )

    ranking = []

    for register, total in total_by_register.items():

        if total == 0:
            continue

        successes = success_by_register[register]

        rate = successes / total

        ranking.append(
            (
                register,
                rate,
                successes,
                total,
            )
        )

    ranking.sort(
        key=lambda item: (
            item[1],
            item[2],
            item[3],
        ),
        reverse=True,
    )

    return [
        register
        for register, _, _, _
        in ranking[:TOP_N_REGISTERS]
    ]

# ============================================================================
# Plot
# ============================================================================
def plot_use_case(
    use_case: str,
    use_case_stats,
) -> None:

    registers = get_top_registers(
        use_case_stats,
        RANKING_CONFIGURATION
    )

    if not registers:
        print(
            f"No registers found for "
            f"{USE_CASE_NAMES[use_case]}"
        )
        return

    # ----------------------------------------------------------------------
    # Compact vertical layout
    # ----------------------------------------------------------------------

    # Distance between Baseline and SECDED 5
    ROW_SPACING = 0.4

    # Distance between two register groups
    REGISTER_SPACING = 0.25

    # Height of each horizontal bar
    BAR_HEIGHT = 0.25

    positions = {}
    register_centers = []

    current_y = 0.0

    for register in registers:

        baseline_y = current_y
        secded_y = current_y + ROW_SPACING

        positions[(register, BASELINE_NAME)] = baseline_y
        positions[(register, SECDED5_NAME)] = secded_y

        register_centers.append(
            (baseline_y + secded_y) / 2
        )

        current_y += (
            ROW_SPACING
            + REGISTER_SPACING
        )

    # ----------------------------------------------------------------------
    # Common X-axis maximum
    # ----------------------------------------------------------------------

    all_values = []

    for fault_model in FAULT_MODEL_ORDER:

        for register in registers:

            for configuration in CONFIGURATION_ORDER:

                value = get_register_value(
                    use_case_stats[
                        configuration
                    ][
                        fault_model
                    ],
                    register,
                )

                if value is not None:
                    all_values.append(value)

    maximum = max(all_values) if all_values else 1.0

    if maximum <= 0:
        maximum = 1.0

    x_max = maximum * 1.08

    # ----------------------------------------------------------------------
    # Figure
    # ----------------------------------------------------------------------

    # Much more compact than before
    figure_height = max(
        4.5,
        len(registers) * 0.42,
    )

    fig, axes = plt.subplots(
        nrows=1,
        ncols=3,
        figsize=(12.5, figure_height),
        sharey=True,
    )

    # Fixed colours:
    # one colour = one configuration
    configuration_colors = {
        BASELINE_NAME: "tab:blue",
        SECDED5_NAME: "tab:orange",
    }

    for column_index, fault_model in enumerate(
        FAULT_MODEL_ORDER
    ):

        ax = axes[column_index]

        for register in registers:

            for configuration in CONFIGURATION_ORDER:

                y = positions[
                    (
                        register,
                        configuration,
                    )
                ]

                statistics = use_case_stats[
                    configuration
                ][
                    fault_model
                ]

                value = get_register_value(
                    statistics,
                    register,
                )

                # ----------------------------------------------------------
                # N/A = not evaluated
                # ----------------------------------------------------------

                if value is None:

                    ax.text(
                        x_max * 0.02,
                        y,
                        "N/A",
                        va="center",
                        ha="left",
                        fontsize=7,
                    )

                    continue

                ax.barh(
                    y,
                    value,
                    height=BAR_HEIGHT,
                    color=configuration_colors[
                        configuration
                    ],
                )

        ax.set_title(
            FAULT_MODEL_NAMES[fault_model],
            fontsize=9,
        )

        ax.set_xlim(
            0,
            x_max,
        )

        ax.grid(
            axis="x",
            alpha=0.20,
        )

        ax.set_axisbelow(True)

        if METRIC == "rate":
            ax.set_xlabel(
                "Successful injections (%)",
                fontsize=8,
            )
        else:
            ax.set_xlabel(
                "Successful injections",
                fontsize=8,
            )

        ax.tick_params(
            axis="x",
            labelsize=7,
        )

    # ----------------------------------------------------------------------
    # Register names
    # ----------------------------------------------------------------------

    # axes[0].set_yticks(
    #     register_centers
    # )

    # axes[0].set_yticklabels(
    #     registers,
    #     fontsize=7,
    # )

    # # Baseline at the top
    # axes[0].invert_yaxis()

    # ----------------------------------------------------------------------
    # Left labels:
    #   Register name | Configuration
    # ----------------------------------------------------------------------

    # We do not use the standard y tick labels.
    axes[0].set_yticks([])

    for register in registers:

        baseline_y = positions[
            (register, BASELINE_NAME)
        ]

        secded_y = positions[
            (register, SECDED5_NAME)
        ]

        center_y = (
            baseline_y + secded_y
        ) / 2

        # Register name: first column
        axes[0].text(
            -0.19,
            center_y,
            register,
            transform=axes[0].get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=7,
            clip_on=False,
        )

        # Baseline: second column
        axes[0].text(
            -0.01,
            baseline_y,
            "Baseline",
            transform=axes[0].get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=6.5,
            clip_on=False,
        )

        # SECDED 5: second column
        axes[0].text(
            -0.01,
            secded_y,
            "SECDED 5",
            transform=axes[0].get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=6.5,
            clip_on=False,
        )

    # ----------------------------------------------------------------------
    # Separators between registers
    # ----------------------------------------------------------------------

    for index in range(
        len(registers) - 1
    ):

        current_register = registers[index]
        next_register = registers[index + 1]

        current_secded_y = positions[
            (
                current_register,
                SECDED5_NAME,
            )
        ]

        next_baseline_y = positions[
            (
                next_register,
                BASELINE_NAME,
            )
        ]

        separator = (
            current_secded_y
            + next_baseline_y
        ) / 2
        
        GROUP_HEIGHT = ROW_SPACING + REGISTER_SPACING

        for ax in axes:
            ax.set_ylim(
                positions[(registers[-1], BASELINE_NAME)]
                + GROUP_HEIGHT / 2,
                positions[(registers[0], BASELINE_NAME)]
                - GROUP_HEIGHT / 2,
            )

    # ----------------------------------------------------------------------
    # Layout
    # ----------------------------------------------------------------------

    fig.tight_layout()

    # Extra room on the left for:
    # register name + Baseline / SECDED 5
    fig.subplots_adjust(
        left=0.24,
        wspace=0.06,
    )

    # ----------------------------------------------------------------------
    # Save
    # ----------------------------------------------------------------------

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_name = (
        OUTPUT_ROOT
        / (
            "figure9_"
            + USE_CASE_OUTPUT_NAMES[
                use_case
            ]
        )
    )

    fig.savefig(
        base_name.with_suffix(".pdf"),
        bbox_inches="tight",
    )

    fig.savefig(
        base_name.with_suffix(".png"),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"Figure generated: "
        f"{base_name.with_suffix('.pdf')}"
    )

    print(
        f"Figure generated: "
        f"{base_name.with_suffix('.png')}"
    )


# ============================================================================
# Main
# ============================================================================
def main() -> None:

    if not RESULTS_ROOT.is_dir():
        raise FileNotFoundError(
            f"Results directory not found: "
            f"{RESULTS_ROOT.resolve()}"
        )

    stats = analyse_campaigns()

    for use_case in USE_CASE_NAMES:

        if use_case not in stats:
            continue

        plot_use_case(
            use_case,
            stats[use_case],
        )


if __name__ == "__main__":
    main()