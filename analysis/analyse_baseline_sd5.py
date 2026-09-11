from __future__ import annotations

import csv
import json
import re

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

# Root directory containing all simulation campaign folders
RESULTS_ROOT = Path("results_simulations")

# Output directory
OUTPUT_ROOT = Path("baseline_vs_secded5_results")

# Optional register alias file
REGISTER_ALIASES_FILE = Path("register_aliases.csv")

# status_end value corresponding to a successful attack
SUCCESS_STATUS = 4

# Number of registers displayed in the figures
TOP_N_REGISTERS = 15


# ------------------------------------------------------------
# Use cases
# ------------------------------------------------------------

USE_CASE_NAMES = {
    "buffer_overflow": "Buffer Overflow",
    "secretFunction": "Format String",
}

USE_CASE_SUFFIXES = {
    "buffer_overflow": "bo",
    "secretFunction": "fs",
}


# ------------------------------------------------------------
# Fault models
# ------------------------------------------------------------

FAULT_MODEL_NAMES = {
    "single_bitflip_spatial": "Single-bit / two registers",
    "multi_bitflip_reg": "Multi-bit / one register",
    "multi_bitflip_reg_multi": "Multi-bit / two registers",
}

FAULT_MODEL_ORDER = [
    "single_bitflip_spatial",
    "multi_bitflip_reg",
    "multi_bitflip_reg_multi",
]


# ------------------------------------------------------------
# Configurations kept for this analysis
# ------------------------------------------------------------

BASELINE_NAME = "Baseline"
SECDED5_NAME = "SECDED Strategy 5"

CONFIGURATION_ORDER = [
    BASELINE_NAME,
    SECDED5_NAME,
]


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class CampaignMetadata:
    use_case: str
    protection: str
    strategy: int | None
    fault_model: str
    folder_name: str


@dataclass
class Statistics:
    total_simulations: int
    successes: int
    register_total: Counter
    register_success: Counter


# ============================================================
# SMALL UTILITIES
# ============================================================

def safe_filename(name: str) -> str:
    """
    Convert a string into a filename-safe representation.
    """

    name = name.replace("/", "_")
    name = name.replace("\\", "_")
    name = name.replace("[", "_")
    name = name.replace("]", "")
    name = name.replace(" ", "_")

    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def format_use_case_name(use_case: str) -> str:
    return USE_CASE_NAMES.get(use_case, use_case)


def format_use_case_suffix(use_case: str) -> str:
    return USE_CASE_SUFFIXES.get(
        use_case,
        safe_filename(use_case),
    )


def format_fault_model_name(fault_model: str) -> str:
    return FAULT_MODEL_NAMES.get(
        fault_model,
        fault_model.replace("_", " "),
    )


# ============================================================
# REGISTER ALIASES
# ============================================================

def load_register_aliases(
    csv_path: Path,
) -> dict[tuple[int | None, str, str], str]:
    """
    Load register aliases.

    Expected CSV columns:
        strategy, protection, rtl_name, logical_name

    An empty logical_name means that the original RTL name is kept.
    """

    aliases = {}

    if not csv_path.exists():
        print(
            f"[INFO] Alias file not found: {csv_path}. "
            f"Original register names will be used."
        )
        return aliases

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:

            rtl_name = row.get(
                "rtl_name",
                "",
            ).strip()

            logical_name = row.get(
                "logical_name",
                "",
            ).strip()

            protection = row.get(
                "protection",
                "",
            ).strip().lower()

            strategy_text = row.get(
                "strategy",
                "",
            ).strip()

            if not rtl_name:
                continue

            strategy = None

            if strategy_text:
                try:
                    strategy = int(strategy_text)
                except ValueError:
                    pass

            aliases[
                (
                    strategy,
                    protection,
                    rtl_name,
                )
            ] = (
                logical_name
                if logical_name
                else rtl_name
            )

    print(
        f"[INFO] Loaded {len(aliases)} register aliases."
    )

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

    logical_name = aliases.get(
        key,
        rtl_name,
    )

    return logical_name


# ============================================================
# CAMPAIGN FOLDER PARSING
# ============================================================

def identify_use_case(folder_name: str) -> str | None:

    if folder_name.startswith("buffer_overflow_"):
        return "buffer_overflow"

    if folder_name.startswith("secretFunction_"):
        return "secretFunction"

    return None


def identify_fault_model(folder_name: str) -> str | None:

    # Order matters because multi_bitflip_reg is contained
    # in multi_bitflip_reg_multi.
    for fault_model in [
        "multi_bitflip_reg_multi",
        "single_bitflip_spatial",
        "multi_bitflip_reg",
    ]:

        if fault_model in folder_name:
            return fault_model

    return None


def parse_campaign_folder(
    folder: Path,
) -> CampaignMetadata | None:

    folder_name = folder.name

    use_case = identify_use_case(folder_name)
    fault_model = identify_fault_model(folder_name)

    if use_case is None or fault_model is None:
        return None

    lower_name = folder_name.lower()

    # Baseline / without protection
    if re.search(r"_wop_\d+_", lower_name):
        match = re.search(r"_wop_(\d+)_", lower_name)
        strategy = int(match.group(1)) if match else None

        return CampaignMetadata(
            use_case=use_case,
            protection="wop",
            strategy=strategy,
            fault_model=fault_model,
            folder_name=folder_name,
        )

    # SECDED Strategy 5
    if re.search(r"_secded_5_", lower_name):

        return CampaignMetadata(
            use_case=use_case,
            protection="secded",
            strategy=5,
            fault_model=fault_model,
            folder_name=folder_name,
        )

    # Ignore every other campaign
    return None

# ============================================================
# REGISTER EXTRACTION
# ============================================================

def extract_faulted_registers(
    simulation: dict,
    metadata: CampaignMetadata,
    aliases: dict,
) -> list[str]:

    registers = []

    # --------------------------------------------------------
    # Single field
    # --------------------------------------------------------

    register = simulation.get(
        "faulted_register"
    )

    if register:

        registers.append(
            apply_register_alias(
                str(register),
                metadata.strategy,
                metadata.protection,
                aliases,
            )
        )

    # --------------------------------------------------------
    # Indexed fields:
    # faulted_register_0, faulted_register_1, ...
    # --------------------------------------------------------

    indexed_registers = []

    for key, value in simulation.items():

        match = re.fullmatch(
            r"faulted_register_(\d+)",
            key,
        )

        if (
            match
            and value is not None
            and value != ""
        ):

            indexed_registers.append(
                (
                    int(match.group(1)),
                    str(value),
                )
            )

    indexed_registers.sort(
        key=lambda item: item[0]
    )

    for _, register in indexed_registers:

        registers.append(
            apply_register_alias(
                register,
                metadata.strategy,
                metadata.protection,
                aliases,
            )
        )

    # Remove duplicate names within the same simulation.
    #
    # Example:
    # if the same register appears twice, the simulation still
    # counts only once as a simulation targeting this register.
    return list(dict.fromkeys(registers))


# ============================================================
# JSON ANALYSIS
# ============================================================

def analyse_json_file(
    json_path: Path,
    metadata: CampaignMetadata,
    aliases: dict,
) -> Statistics:

    statistics = Statistics(
        total_simulations=0,
        successes=0,
        register_total=Counter(),
        register_success=Counter(),
    )

    try:

        with json_path.open(
            "r",
            encoding="utf-8",
        ) as json_file:

            data = json.load(json_file)

    except (
        json.JSONDecodeError,
        OSError,
    ) as error:

        print(
            f"[WARNING] Cannot read {json_path}: {error}"
        )

        return statistics

    # JSON can either directly contain simulations
    # or contain them under a "simulations" field.
    if isinstance(data, dict):

        if "simulations" in data:
            simulations = data["simulations"]
        else:
            simulations = list(
                data.values()
            )

    elif isinstance(data, list):

        simulations = data

    else:
        return statistics

    for simulation_index, simulation in enumerate(
        simulations
    ):

        if not isinstance(
            simulation,
            dict,
        ):
            continue

        # simulation_0 / first simulation is the reference
        # execution and must not be counted as a fault injection.
        #
        # If simulation IDs are present, use them.
        simulation_id = simulation.get(
            "simulation_id",
            simulation.get(
                "simulation",
                simulation.get(
                    "id"
                ),
            ),
        )

        if simulation_id in [
            0,
            "0",
            "simulation_0",
        ]:
            continue

        # If no explicit ID exists, preserve previous behaviour:
        # first entry is the reference simulation.
        if (
            simulation_id is None
            and simulation_index == 0
        ):
            continue

        registers = extract_faulted_registers(
            simulation,
            metadata,
            aliases,
        )

        if not registers:
            continue

        statistics.total_simulations += 1

        success = (
            simulation.get("status_end")
            == SUCCESS_STATUS
        )

        if success:
            statistics.successes += 1

        for register in registers:

            statistics.register_total[
                register
            ] += 1

            if success:

                statistics.register_success[
                    register
                ] += 1

    return statistics


# ============================================================
# CONFIGURATION NAME
# ============================================================

def get_configuration_name(
    metadata: CampaignMetadata,
) -> str:

    if metadata.protection == "wop":
        return BASELINE_NAME

    if (
        metadata.protection == "secded"
        and metadata.strategy == 5
    ):
        return SECDED5_NAME

    raise ValueError(
        f"Unexpected configuration: "
        f"{metadata.protection}, strategy {metadata.strategy}"
    )


# ============================================================
# CSV EXPORT
# ============================================================

def export_use_case_csv(
    use_case: str,
    success_data,
    total_data,
    output_directory: Path,
) -> Path:

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    suffix = format_use_case_suffix(
        use_case
    )

    output_path = (
        output_directory
        / f"register_statistics_{suffix}.csv"
    )

    rows = []

    for configuration in CONFIGURATION_ORDER:

        for fault_model in FAULT_MODEL_ORDER:

            totals = total_data[
                use_case
            ][
                configuration
            ][
                fault_model
            ]

            successes = success_data[
                use_case
            ][
                configuration
            ][
                fault_model
            ]

            for register in sorted(
                totals.keys()
            ):

                total = totals.get(
                    register,
                    0,
                )

                if total == 0:
                    continue

                success = successes.get(
                    register,
                    0,
                )

                success_rate = (
                    100.0
                    * success
                    / total
                )

                rows.append(
                    {
                        "register": register,
                        "use_case": use_case,
                        "configuration": configuration,
                        "fault_model": fault_model,
                        "successes": success,
                        "total_simulations": total,
                        "success_rate_percent": f"{success_rate:.6f}",
                    }
                )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        fieldnames = [
            "register",
            "use_case",
            "configuration",
            "fault_model",
            "successes",
            "total_simulations",
            "success_rate_percent",
        ]

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"[CSV] {output_path}"
    )

    return output_path


# ============================================================
# GLOBAL SUCCESS RATE PER REGISTER
# ============================================================

def compute_global_register_rates(
    use_case: str,
    success_data,
    total_data,
) -> dict[str, dict[str, float]]:
    """
    Compute one global rate per register and configuration,
    aggregating all fault models:

        total successes / total simulations

    The three fault models are NOT averaged.
    """

    registers = set()

    for configuration in CONFIGURATION_ORDER:

        for fault_model in FAULT_MODEL_ORDER:

            registers.update(
                total_data[
                    use_case
                ][
                    configuration
                ][
                    fault_model
                ].keys()
            )

    rates = defaultdict(dict)

    for register in registers:

        for configuration in CONFIGURATION_ORDER:

            total_success = 0
            total_simulations = 0

            for fault_model in FAULT_MODEL_ORDER:

                total_success += (
                    success_data[
                        use_case
                    ][
                        configuration
                    ][
                        fault_model
                    ].get(
                        register,
                        0,
                    )
                )

                total_simulations += (
                    total_data[
                        use_case
                    ][
                        configuration
                    ][
                        fault_model
                    ].get(
                        register,
                        0,
                    )
                )

            if total_simulations > 0:

                rates[
                    register
                ][
                    configuration
                ] = (
                    100.0
                    * total_success
                    / total_simulations
                )

    return rates


def compute_register_rates_by_fault_model(
    use_case: str,
    configuration: str,
    success_data,
    total_data,
) -> dict[str, dict[str, float]]:
    """
    Returns:

        register -> fault_model -> success_rate_percent

    Only combinations that were actually simulated are included.
    """

    rates = defaultdict(dict)

    for fault_model in FAULT_MODEL_ORDER:

        success_counter = (
            success_data
            .get(use_case, {})
            .get(configuration, {})
            .get(fault_model, Counter())
        )

        total_counter = (
            total_data
            .get(use_case, {})
            .get(configuration, {})
            .get(fault_model, Counter())
        )

        all_registers = (
            set(success_counter.keys())
            | set(total_counter.keys())
        )

        for register in all_registers:

            total = total_counter.get(register, 0)

            # Important:
            # total == 0 means "not evaluated",
            # NOT "0% successful attacks".
            if total == 0:
                continue

            successes = success_counter.get(register, 0)

            rate = 100.0 * successes / total

            rates[register][fault_model] = rate

    return rates


def compute_register_global_ranking(
    use_case: str,
    configuration: str,
    success_data,
    total_data,
) -> dict[str, float]:
    """
    Computes one global sensitivity value per register.

    The value is used ONLY to rank registers in the figure.

    It is calculated as:

        sum(successes) / sum(total simulations)

    across all available fault models.
    """

    global_success = Counter()
    global_total = Counter()

    for fault_model in FAULT_MODEL_ORDER:

        success_counter = (
            success_data
            .get(use_case, {})
            .get(configuration, {})
            .get(fault_model, Counter())
        )

        total_counter = (
            total_data
            .get(use_case, {})
            .get(configuration, {})
            .get(fault_model, Counter())
        )

        global_success.update(success_counter)
        global_total.update(total_counter)

    rates = {}

    for register, total in global_total.items():

        if total == 0:
            continue

        successes = global_success.get(register, 0)

        rates[register] = (
            100.0 * successes / total
        )

    return rates

# ============================================================
# BASELINE VS SECDED 5 FIGURE
# ============================================================

def plot_baseline_vs_secded5(
    use_case: str,
    success_data,
    total_data,
    output_directory: Path,
    ranking_configuration: str,
    top_n: int = TOP_N_REGISTERS,
) -> None:

    rates = compute_global_register_rates(
        use_case,
        success_data,
        total_data,
    )

    # --------------------------------------------------------
    # Keep only registers that exist in BOTH configurations.
    #
    # This ensures a real baseline-vs-SECDED5 comparison.
    # --------------------------------------------------------

    common_registers = {
        register: config_rates
        for register, config_rates in rates.items()
        if (
            BASELINE_NAME in config_rates
            and SECDED5_NAME in config_rates
        )
    }

    if not common_registers:

        print(
            f"[WARNING] No common registers found for "
            f"{use_case}."
        )
        return

    # --------------------------------------------------------
    # Rank registers according to baseline vulnerability.
    #
    # This answers:
    # Which registers are the most vulnerable before protection?
    # --------------------------------------------------------

    selected = sorted(
        common_registers.items(),
        key=lambda item: item[1][ranking_configuration],
        reverse=True,
    )[:top_n]

    # Name used in the figure title and output filename
    if ranking_configuration == BASELINE_NAME:
        ranking_title = "Baseline"
        ranking_suffix = "baseline"
    else:
        ranking_title = "SECDED Strategy 5"
        ranking_suffix = "secded5"

    # Reverse for horizontal plot:
    # highest register appears at the top.
    selected = list(
        reversed(selected)
    )

    registers = [
        register
        for register, _ in selected
    ]

    baseline_rates = [
        rate_data[BASELINE_NAME]
        for _, rate_data in selected
    ]

    secded_rates = [
        rate_data[SECDED5_NAME]
        for _, rate_data in selected
    ]

    y_positions = list(
        range(len(registers))
    )

    bar_height = 0.38

    fig_height = max(
        5,
        len(registers) * 0.45,
    )

    fig, ax = plt.subplots(
        figsize=(10, fig_height)
    )

    baseline_bars = ax.barh(
        [
            y - bar_height / 2
            for y in y_positions
        ],
        baseline_rates,
        height=bar_height,
        label=BASELINE_NAME,
    )

    secded_bars = ax.barh(
        [
            y + bar_height / 2
            for y in y_positions
        ],
        secded_rates,
        height=bar_height,
        label=SECDED5_NAME,
    )

    ax.set_yticks(
        y_positions
    )

    ax.set_yticklabels(
        registers
    )

    ax.set_xlabel(
        "Successful attack rate (%)"
    )

    ax.set_title(
        f"Register sensitivity ranked by {ranking_title} — "
        f"{format_use_case_name(use_case)}"
    )

    ax.legend()

    # --------------------------------------------------------
    # Percentage labels
    # --------------------------------------------------------

    for bars in [
        baseline_bars,
        secded_bars,
    ]:

        for bar in bars:

            value = bar.get_width()

            if value >= 0.10:

                ax.text(
                    value,
                    bar.get_y()
                    + bar.get_height() / 2,
                    f" {value:.2f}%",
                    va="center",
                    ha="left",
                    fontsize=7,
                )

    ax.grid(
        axis="x",
        linestyle=":",
        alpha=0.4,
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    suffix = format_use_case_suffix(
        use_case
    )

    png_path = (
        output_directory
        / f"register_success_rate_ranked_by_{ranking_suffix}_{suffix}.png"
    )

    pdf_path = (
        output_directory
        / f"register_success_rate_ranked_by_{ranking_suffix}_{suffix}.pdf"
    )

    fig.tight_layout()

    fig.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[FIGURE] {png_path}"
    )


def plot_register_sensitivity_by_fault_model(
    use_case: str,
    configuration: str,
    success_data,
    total_data,
    output_directory: Path,
    top_n: int = TOP_N_REGISTERS,
) -> None:

    # --------------------------------------------------------
    # Detailed rates:
    # register -> fault model -> success rate
    # --------------------------------------------------------

    rates_by_fault_model = (
        compute_register_rates_by_fault_model(
            use_case=use_case,
            configuration=configuration,
            success_data=success_data,
            total_data=total_data,
        )
    )

    # --------------------------------------------------------
    # Global rate used ONLY for ranking the registers
    # --------------------------------------------------------

    ranking = compute_register_global_ranking(
        use_case=use_case,
        configuration=configuration,
        success_data=success_data,
        total_data=total_data,
    )

    if not ranking:
        print(
            f"[WARNING] No register data for "
            f"{use_case} / {configuration}"
        )
        return

    # --------------------------------------------------------
    # Select Top N registers from THIS configuration.
    #
    # Therefore:
    # - Baseline is ranked using Baseline registers
    # - SECDED 5 is ranked using SECDED 5 registers
    #
    # SECDED-specific registers such as hc_o_* are preserved.
    # --------------------------------------------------------

    selected_registers = sorted(
        ranking,
        key=ranking.get,
        reverse=True,
    )[:top_n]

    # Reverse because barh displays the first item at the bottom
    selected_registers = list(
        reversed(selected_registers)
    )

    # --------------------------------------------------------
    # Prepare plot
    # --------------------------------------------------------

    n_registers = len(selected_registers)

    figure_height = max(
        5.0,
        0.55 * n_registers,
    )

    fig, ax = plt.subplots(
        figsize=(11, figure_height)
    )

    y_positions = list(
        range(n_registers)
    )

    number_of_models = len(
        FAULT_MODEL_ORDER
    )

    total_group_height = 0.72

    bar_height = (
        total_group_height
        / number_of_models
    )

    # --------------------------------------------------------
    # Draw one horizontal bar per fault model
    # --------------------------------------------------------

    for model_index, fault_model in enumerate(
        FAULT_MODEL_ORDER
    ):

        offset = (
            model_index
            - (number_of_models - 1) / 2
        ) * bar_height

        positions = [
            y + offset
            for y in y_positions
        ]

        values = []

        for register in selected_registers:

            register_rates = (
                rates_by_fault_model.get(
                    register,
                    {}
                )
            )

            # NaN means:
            # not simulated for this register/model.
            value = register_rates.get(
                fault_model,
                float("nan"),
            )

            values.append(value)

        bars = ax.barh(
            positions,
            values,
            height=bar_height * 0.90,
            label=format_fault_model_name(
                fault_model
            ),
        )

        # ----------------------------------------------------
        # Add rate labels
        # ----------------------------------------------------

        for bar, value in zip(
            bars,
            values,
        ):

            # NaN = non evaluated
            if value != value:
                continue

            if value < 0.01:
                continue

            ax.text(
                value,
                bar.get_y()
                + bar.get_height() / 2,
                f" {value:.2f}%",
                va="center",
                ha="left",
                fontsize=8,
            )

    # --------------------------------------------------------
    # Axis labels
    # --------------------------------------------------------

    ax.set_yticks(y_positions)

    ax.set_yticklabels(
        selected_registers
    )

    ax.set_xlabel(
        "Successful attack rate (%)"
    )

    ax.set_ylabel(
        "Faulted register"
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if configuration == BASELINE_NAME:
        configuration_title = (
            "Baseline"
        )
        configuration_suffix = (
            "baseline"
        )

    elif configuration == SECDED5_NAME:
        configuration_title = (
            "SECDED Strategy 5"
        )
        configuration_suffix = (
            "secded5"
        )

    else:
        configuration_title = (
            configuration
        )
        configuration_suffix = (
            safe_filename(configuration)
        )

    ax.set_title(
        f"Register sensitivity — "
        f"{configuration_title} — "
        f"{format_use_case_name(use_case)}"
    )

    ax.legend(
        title="Fault model"
    )

    ax.set_xlim(left=0)

    ax.grid(
        axis="x",
        alpha=0.25,
    )

    fig.tight_layout()

    # --------------------------------------------------------
    # Output filenames
    # --------------------------------------------------------

    suffix = format_use_case_suffix(
        use_case
    )

    png_path = (
        output_directory
        / (
            "register_sensitivity_"
            f"{configuration_suffix}_"
            f"{suffix}.png"
        )
    )

    pdf_path = (
        output_directory
        / (
            "register_sensitivity_"
            f"{configuration_suffix}_"
            f"{suffix}.pdf"
        )
    )

    fig.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[FIGURE] {png_path}"
    )
    print(
        f"[FIGURE] {pdf_path}"
    )

# ============================================================
# OPTIONAL: ONE CSV PER REGISTER
# ============================================================

def export_one_csv_per_register(
    use_case: str,
    success_data,
    total_data,
    output_directory: Path,
) -> None:

    suffix = format_use_case_suffix(
        use_case
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    registers = set()

    for configuration in CONFIGURATION_ORDER:

        for fault_model in FAULT_MODEL_ORDER:

            registers.update(
                total_data[
                    use_case
                ][
                    configuration
                ][
                    fault_model
                ].keys()
            )

    for register in sorted(registers):

        rows = []

        for configuration in CONFIGURATION_ORDER:

            for fault_model in FAULT_MODEL_ORDER:

                total = (
                    total_data[
                        use_case
                    ][
                        configuration
                    ][
                        fault_model
                    ].get(
                        register,
                        0,
                    )
                )

                # Do not interpret a non-simulated register/model
                # combination as 0% success.
                if total == 0:
                    continue

                success = (
                    success_data[
                        use_case
                    ][
                        configuration
                    ][
                        fault_model
                    ].get(
                        register,
                        0,
                    )
                )

                rate = (
                    100.0
                    * success
                    / total
                )

                rows.append(
                    {
                        "register": register,
                        "use_case": use_case,
                        "configuration": configuration,
                        "fault_model": fault_model,
                        "successes": success,
                        "total_simulations": total,
                        "success_rate_percent": f"{rate:.6f}",
                    }
                )

        if not rows:
            continue

        filename = (
            f"{safe_filename(register)}"
            f"_{suffix}.csv"
        )

        output_path = (
            output_directory
            / filename
        )

        with output_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:

            fieldnames = [
                "register",
                "use_case",
                "configuration",
                "fault_model",
                "successes",
                "total_simulations",
                "success_rate_percent",
            ]

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(rows)


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=============================================="
    )
    print(
        " Baseline vs SECDED Strategy 5 analysis"
    )
    print(
        "=============================================="
    )

    aliases = load_register_aliases(
        REGISTER_ALIASES_FILE
    )

    print(
        f"[ALIASES] {len(aliases)} aliases loaded"
    )

    # Structure:
    #
    # use_case
    #   -> configuration
    #       -> fault_model
    #           -> register : count

    register_success = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                Counter
            )
        )
    )

    register_total = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                Counter
            )
        )
    )

    analysed_campaigns = 0
    analysed_files = 0

    for use_case_folder in sorted(
        RESULTS_ROOT.iterdir()
    ):

        if not use_case_folder.is_dir():
            continue

        if use_case_folder.name not in USE_CASE_NAMES:
            continue

        print(
            f"\n[USE CASE] {use_case_folder.name}"
        )

        for campaign_folder in sorted(
            use_case_folder.iterdir()
        ):

            if not campaign_folder.is_dir():
                continue

            metadata = parse_campaign_folder(
                campaign_folder
            )

            # Ignore every campaign except baseline
            # and SECDED Strategy 5
            if metadata is None:
                continue

            configuration = get_configuration_name(
                metadata
            )

            print(
                f"\n[CAMPAIGN] "
                f"{campaign_folder.name}"
            )

            print(
                f"           use case      = "
                f"{metadata.use_case}"
            )

            print(
                f"           configuration = "
                f"{configuration}"
            )

            print(
                f"           fault model   = "
                f"{metadata.fault_model}"
            )

            analysed_campaigns += 1

            json_files = sorted(
                campaign_folder.glob("*.json")
            )

            print(
                f"           JSON files    = "
                f"{len(json_files)}"
            )

            for json_path in json_files:

                statistics = analyse_json_file(
                    json_path,
                    metadata,
                    aliases,
                )

                register_success[
                    metadata.use_case
                ][
                    configuration
                ][
                    metadata.fault_model
                ].update(
                    statistics.register_success
                )

                register_total[
                    metadata.use_case
                ][
                    configuration
                ][
                    metadata.fault_model
                ].update(
                    statistics.register_total
                )

                analysed_files += 1

    # --------------------------------------------------------
    # Outputs
    # --------------------------------------------------------
    print("\n===== SECDED 5 REGISTER CHECK =====")
    for use_case in USE_CASE_NAMES:

        print(
            f"\n[{format_use_case_name(use_case)}]"
        )

        registers = set()

        for fault_model in FAULT_MODEL_ORDER:

            registers.update(
                register_total[
                    use_case
                ][
                    SECDED5_NAME
                ][
                    fault_model
                ].keys()
            )

        hamming_registers = sorted(
            register
            for register in registers
            if (
                "hc_" in register.lower()
                or "hamming" in register.lower()
            )
        )

        print(
            f"SECDED 5 registers found: "
            f"{len(registers)}"
        )

        print(
            f"Hamming registers found: "
            f"{len(hamming_registers)}"
        )

        for register in hamming_registers:
            print(
                f"    {register}"
            )

    for use_case in USE_CASE_NAMES:

        use_case_directory = (
            OUTPUT_ROOT
            / safe_filename(use_case)
        )

        # One complete CSV for the use case
        export_use_case_csv(
            use_case,
            register_success,
            register_total,
            use_case_directory,
        )

        # One CSV per register
        export_one_csv_per_register(
            use_case,
            register_success,
            register_total,
            use_case_directory
            / "registers",
        )

        # Baseline
        plot_register_sensitivity_by_fault_model(
            use_case=use_case,
            configuration=BASELINE_NAME,
            success_data=register_success,
            total_data=register_total,
            output_directory=use_case_directory,
        )

        # SECDED Strategy 5
        plot_register_sensitivity_by_fault_model(
            use_case=use_case,
            configuration=SECDED5_NAME,
            success_data=register_success,
            total_data=register_total,
            output_directory=use_case_directory,
        )

    print()
    print(
        "=============================================="
    )
    print(
        f"Campaigns analysed : {analysed_campaigns}"
    )
    print(
        f"JSON files analysed: {analysed_files}"
    )
    print(
        f"Results directory  : {OUTPUT_ROOT}"
    )
    print(
        "=============================================="
    )


if __name__ == "__main__":
    main()