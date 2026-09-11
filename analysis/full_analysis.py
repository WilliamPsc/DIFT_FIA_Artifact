from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUCCESS_STATUS = 4

# Le script cherche d'abord results_simulations, puis results_simulation.
POSSIBLE_ROOT_DIRECTORIES = (
    Path("results_simulations"),
    Path("results_simulation"),
)

OUTPUT_DIRECTORY = Path("register_sensitivity_results")
REGISTER_ALIASES_FILE = Path("register_aliases.csv")

# Nombre de registres affichés dans chaque histogramme.
TOP_N_REGISTERS = 15
TOP_N_PAIRS = 10

# True : affiche les noms complets du type if_stage_i/pc_if_o_tag.
# False : affiche seulement pc_if_o_tag.
KEEP_MODULE_NAME = True

# Couleurs utilisées dans les histogrammes empilés.
STRATEGY_COLORS = {
    1: "tab:blue",
    2: "tab:orange",
    3: "tab:green",
    4: "tab:red",
    5: "tab:purple",
}

STRATEGY_ORDER = [1, 2, 3, 4, 5]

FAULT_MODEL_ORDER = [
    "single_bitflip_spatial",
    "multi_bitflip_reg",
    "multi_bitflip_reg_multi",
]

FAULT_MODEL_COLORS = {
    "single_bitflip_spatial": "tab:blue",
    "multi_bitflip_reg": "tab:orange",
    "multi_bitflip_reg_multi": "tab:green",
}


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

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
    simulations: int
    successful_simulations: int
    register_total: Counter[str]
    register_success: Counter[str]
    pair_total: Counter[tuple[str, ...]]
    pair_success: Counter[tuple[str, ...]]

    @classmethod
    def create(cls) -> "Statistics":
        return cls(
            simulations=0,
            successful_simulations=0,
            register_total=Counter(),
            register_success=Counter(),
            pair_total=Counter(),
            pair_success=Counter(),
        )

    def merge(self, other: "Statistics") -> None:
        self.simulations += other.simulations
        self.successful_simulations += other.successful_simulations
        self.register_total.update(other.register_total)
        self.register_success.update(other.register_success)
        self.pair_total.update(other.pair_total)
        self.pair_success.update(other.pair_success)


# ---------------------------------------------------------------------------
# Détection et analyse des noms de dossiers
# ---------------------------------------------------------------------------

def find_root_directory() -> Path:
    for directory in POSSIBLE_ROOT_DIRECTORIES:
        if directory.is_dir():
            return directory

    expected = " ou ".join(str(path) for path in POSSIBLE_ROOT_DIRECTORIES)

    raise FileNotFoundError(
        f"Impossible de trouver le dossier {expected}.\n"
        "Place le script dans le dossier père de results_simulations/."
    )


def parse_campaign_folder(
    folder: Path,
    use_case: str,
) -> CampaignMetadata | None:
    """
    Exemples reconnus :

    secretFunction_hamming_5_multi_bitflip_reg_multi_2

    buffer_overflow_hamming_5_multi_bitflip_reg_multi_2
    """

    prefix = f"{use_case}_"

    if not folder.name.startswith(prefix):
        return None

    remaining_name = folder.name[len(prefix):]

    # Le nom restant doit être :
    # protection_stratégie_modèle_de_faute_suffixe
    #
    # La protection peut également contenir des underscores.
    # On identifie la stratégie grâce au premier champ numérique.
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


# ---------------------------------------------------------------------------
# Lecture des simulations
# ---------------------------------------------------------------------------

def simplify_register_name(register_path: str) -> str:
    """
    Conserve au maximum les deux derniers éléments du chemin.

    Exemple :
    id_stage_i/registers_i_tag/hamming_code_encoder_rf_tag/hc_o_rf_tag

    devient :
    hamming_code_encoder_rf_tag/hc_o_rf_tag
    """

    # Suppression des slashs placés au début ou à la fin.
    clean_path = register_path.strip("/")

    # Découpage du chemin en différents niveaux.
    path_parts = [
        part
        for part in clean_path.split("/")
        if part
    ]

    # Un seul niveau disponible.
    if len(path_parts) == 1:
        return path_parts[0]

    # Conservation des deux derniers niveaux.
    return "/".join(path_parts[-2:])


def simulation_sort_key(item: tuple[str, Any]) -> int:
    key = item[0]

    match = re.fullmatch(r"simulation_(\d+)", key)

    if match is None:
        return -1

    return int(match.group(1))


def extract_faulted_registers(
    simulation: dict[str, Any],
    strategy: int,
    protection: str,
    aliases: dict[tuple[int, str, str], str],
) -> list[str]:
    """
    Formats reconnus :
      - faulted_register
      - faulted_register_0
      - faulted_register_1
      - etc.
    """

    indexed_registers: list[tuple[int, str]] = []

    def prepare_register(register_path: str) -> str:
        rtl_name = simplify_register_name(register_path)

        return apply_register_alias(
            rtl_name=rtl_name,
            strategy=strategy,
            protection=protection,
            aliases=aliases,
        )

    # Format avec un seul registre.
    single_register = simulation.get("faulted_register")

    if isinstance(single_register, str):
        indexed_registers.append(
            (
                0,
                prepare_register(single_register),
            )
        )

    # Format avec plusieurs registres.
    pattern = re.compile(r"^faulted_register_(\d+)$")

    for key, value in simulation.items():
        match = pattern.fullmatch(key)

        if match is None or not isinstance(value, str):
            continue

        register_index = int(match.group(1))

        indexed_registers.append(
            (
                register_index,
                prepare_register(value),
            )
        )

    indexed_registers.sort(key=lambda element: element[0])

    unique_registers: list[str] = []
    seen_registers: set[str] = set()

    for _, register_name in indexed_registers:
        if register_name in seen_registers:
            continue

        seen_registers.add(register_name)
        unique_registers.append(register_name)

    return unique_registers


def analyse_json_file(
    json_path: Path,
    strategy: int,
    protection: str,
    aliases: dict[tuple[int, str, str], str],
) -> Statistics:
    statistics = Statistics.create()

    try:
        with json_path.open("r", encoding="utf-8") as file:
            content = json.load(file)

    except json.JSONDecodeError as error:
        print(f"[JSON invalide] {json_path}: {error}")
        return statistics

    except OSError as error:
        print(f"[Erreur de lecture] {json_path}: {error}")
        return statistics

    if not isinstance(content, dict):
        print(f"[Format inattendu] {json_path}")
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
        # La simulation 0 est la simulation de référence non fautée.
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

        # Une simulation sans champ faulted_register_X n'est pas exploitable
        # pour l'analyse de sensibilité.
        if not registers:
            continue

        statistics.simulations += 1

        is_success = simulation.get("status_end") == SUCCESS_STATUS

        if is_success:
            statistics.successful_simulations += 1

        for register in registers:
            statistics.register_total[register] += 1

            if is_success:
                statistics.register_success[register] += 1

        # On utilise un tuple trié afin que (A, B) et (B, A)
        # désignent le même couple.
        pair = tuple(sorted(registers))

        if len(pair) >= 2:
            statistics.pair_total[pair] += 1

            if is_success:
                statistics.pair_success[pair] += 1

    return statistics


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value.strip("_")


def build_register_rows(
    statistics: Statistics,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for register, total in statistics.register_total.items():
        successes = statistics.register_success[register]
        success_rate = successes / total if total else 0.0

        rows.append(
            {
                "register": register,
                "successful_simulations": successes,
                "total_simulations": total,
                "success_rate": success_rate,
                "success_rate_percent": 100.0 * success_rate,
            }
        )

    rows.sort(
        key=lambda row: (
            row["success_rate"],
            row["successful_simulations"],
            row["total_simulations"],
        ),
        reverse=True,
    )

    return rows


def build_pair_rows(
    statistics: Statistics,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for pair, total in statistics.pair_total.items():
        successes = statistics.pair_success[pair]
        success_rate = successes / total if total else 0.0

        rows.append(
            {
                "register_pair": " + ".join(pair),
                "successful_simulations": successes,
                "total_simulations": total,
                "success_rate": success_rate,
                "success_rate_percent": 100.0 * success_rate,
            }
        )

    rows.sort(
        key=lambda row: (
            row["success_rate"],
            row["successful_simulations"],
            row["total_simulations"],
        ),
        reverse=True,
    )

    return rows


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def write_summary_file(
    path: Path,
    statistics: Statistics,
) -> None:
    success_rate = (
        statistics.successful_simulations / statistics.simulations
        if statistics.simulations
        else 0.0
    )

    with path.open("w", encoding="utf-8") as file:
        file.write(f"Simulations analysed: {statistics.simulations}\n")
        file.write(
            "Successful simulations: "
            f"{statistics.successful_simulations}\n"
        )
        file.write(
            f"Overall success rate: {100.0 * success_rate:.6f}%\n"
        )
        file.write(
            f"Distinct registers: {len(statistics.register_total)}\n"
        )
        file.write(
            f"Distinct register pairs: {len(statistics.pair_total)}\n"
        )


def write_register_alias_template(
    path: Path,
    register_names_by_strategy: dict[tuple[int, str], set[str]],
) -> None:
    """
    Génère un modèle de fichier register_aliases.csv.

    Une ligne est créée pour chaque couple :
        stratégie + nom RTL

    La colonne logical_name est initialement vide et doit être
    complétée manuellement lorsque plusieurs noms RTL représentent
    le même registre logique.
    """

    rows = []

    for (strategy, protection), register_names in sorted(
        register_names_by_strategy.items()
    ):
        for register_name in sorted(register_names):
            rows.append(
                {
                    "strategy": strategy,
                    "protection": protection,
                    "rtl_name": register_name,
                    "logical_name": "",
                }
            )

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "strategy",
                "protection",
                "rtl_name",
                "logical_name",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)


def load_register_aliases(
    path: Path,
) -> dict[tuple[int, str, str], str]:
    """
    Charge les correspondances depuis register_aliases.csv.

    Clé :
        (strategy, protection, rtl_name)

    Valeur :
        logical_name
    """

    aliases: dict[tuple[int, str, str], str] = {}

    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier d'alias introuvable : {path.resolve()}"
        )

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        expected_columns = {
            "strategy",
            "protection",
            "rtl_name",
            "logical_name",
        }

        actual_columns = set(reader.fieldnames or [])

        missing_columns = expected_columns - actual_columns

        if missing_columns:
            raise ValueError(
                "Colonnes manquantes dans register_aliases.csv : "
                + ", ".join(sorted(missing_columns))
            )

        for line_number, row in enumerate(reader, start=2):
            strategy_text = row["strategy"].strip()
            protection = row["protection"].strip().lower()
            rtl_name = row["rtl_name"].strip()
            logical_name = row["logical_name"].strip()

            if not strategy_text or not protection or not rtl_name:
                print(
                    f"[Alias ignoré, ligne {line_number}] "
                    "stratégie, protection ou nom RTL manquant."
                )
                continue

            try:
                strategy = int(strategy_text)
            except ValueError:
                print(
                    f"[Alias ignoré, ligne {line_number}] "
                    f"stratégie invalide : {strategy_text}"
                )
                continue

            # Une valeur logique vide signifie :
            # conserver le nom RTL original.
            if not logical_name:
                logical_name = rtl_name

            key = (
                strategy,
                protection,
                rtl_name,
            )

            if key in aliases:
                print(
                    f"[Alias dupliqué, ligne {line_number}] "
                    f"{key}. La dernière valeur sera utilisée."
                )

            aliases[key] = logical_name

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


def format_fault_model_name(fault_model: str) -> str:
    names = {
        "single_bitflip_spatial":
            "Single-bit / two registers",

        "multi_bitflip_reg":
            "Multi-bit / one register",

        "multi_bitflip_reg_multi":
            "Multi-bit / two registers",
    }

    return names.get(
        fault_model,
        fault_model.replace("_", " ")
    )


def format_use_case_suffix(use_case: str) -> str:
    suffixes = {
        "buffer_overflow": "bo",
        "secretFunction": "fs",
    }

    return suffixes.get(
        use_case,
        safe_filename(use_case),
    )


def export_register_statistics_csv(
    register_success_detailed,
    register_total_detailed,
    output_directory: Path,
) -> None:

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for use_case, protection_data in register_total_detailed.items():

        use_case_suffix = format_use_case_suffix(use_case)

        # Find every register evaluated for this use case
        registers = set()

        for strategy_data in protection_data.values():
            for fault_model_data in strategy_data.values():
                for register_counter in fault_model_data.values():
                    registers.update(
                        register_counter.keys()
                    )

        for register in sorted(registers):

            rows = []

            for protection, strategy_data in protection_data.items():

                for strategy, fault_model_data in strategy_data.items():

                    for fault_model, totals in fault_model_data.items():

                        total = totals.get(
                            register,
                            0,
                        )

                        # This register was not evaluated for this
                        # combination.
                        if total == 0:
                            continue

                        success = (
                            register_success_detailed
                            [use_case]
                            [protection]
                            [strategy]
                            [fault_model]
                            .get(register, 0)
                        )

                        success_rate = (
                            100.0
                            * success
                            / total
                        )

                        rows.append({
                            "register": register,
                            "use_case": use_case,
                            "protection": protection,
                            "strategy": strategy,
                            "fault_model": fault_model,
                            "successes": success,
                            "total_simulations": total,
                            "success_rate_percent": f"{success_rate:.6f}",
                        })

            if not rows:
                continue

            rows.sort(
                key=lambda row: (
                    row["protection"],
                    row["strategy"],
                    row["fault_model"],
                )
            )

            safe_register = safe_filename(
                register
            )

            output_path = (
                output_directory
                / f"{safe_register}_{use_case_suffix}.csv"
            )

            with output_path.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as csv_file:

                fieldnames = [
                    "register",
                    "use_case",
                    "protection",
                    "strategy",
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
        f"[CSV] Detailed register statistics exported to "
        f"{output_directory}"
    )

# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def plot_register_histogram(
    rows: list[dict[str, Any]],
    output_path: Path,
    title: str,
    top_n: int = TOP_N_REGISTERS,
) -> None:
    if not rows:
        return

    # Pour éviter qu'un registre ciblé une seule fois avec un succès soit
    # automatiquement classé premier, on classe d'abord selon le taux,
    # puis selon le nombre de succès.
    selected_rows = rows[:top_n]

    # On inverse pour que le meilleur registre soit affiché en haut.
    selected_rows = list(reversed(selected_rows))

    labels = [row["register"] for row in selected_rows]
    values = [row["success_rate_percent"] for row in selected_rows]
    totals = [row["total_simulations"] for row in selected_rows]
    successes = [
        row["successful_simulations"]
        for row in selected_rows
    ]

    figure_height = max(5.0, 0.45 * len(selected_rows))

    plt.figure(figsize=(10, figure_height))
    bars = plt.barh(labels, values)

    plt.xlabel("Successful attack rate (%)")
    plt.ylabel("Faulted register")
    plt.title(title)
    plt.xlim(left=0)

    for bar, value, success, total in zip(
        bars,
        values,
        successes,
        totals,
    ):
        plt.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {value:.2f}% ({success}/{total})",
            va="center",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.savefig(
        output_path.with_suffix(".pdf"),
        bbox_inches="tight",
    )
    plt.close()


def plot_register_success_histogram(
    rows: list[dict[str, Any]],
    output_path: Path,
    title: str,
    top_n: int = TOP_N_REGISTERS,
) -> None:
    if not rows:
        return

    # Ici, on reclasse selon le nombre brut de succès.
    selected_rows = sorted(
        rows,
        key=lambda row: (
            row["successful_simulations"],
            row["success_rate_percent"],
        ),
        reverse=True,
    )[:top_n]

    # On inverse pour que le registre ayant le plus de succès
    # soit affiché en haut.
    selected_rows = list(reversed(selected_rows))

    labels = [row["register"] for row in selected_rows]
    values = [
        row["successful_simulations"]
        for row in selected_rows
    ]
    totals = [
        row["total_simulations"]
        for row in selected_rows
    ]
    rates = [
        row["success_rate_percent"]
        for row in selected_rows
    ]

    figure_height = max(5.0, 0.45 * len(selected_rows))

    plt.figure(figsize=(10, figure_height))
    bars = plt.barh(labels, values)

    plt.xlabel("Number of successful attacks")
    plt.ylabel("Faulted register")
    plt.title(title)
    plt.xlim(left=0)

    for bar, value, rate, total in zip(
        bars,
        values,
        rates,
        totals,
    ):
        plt.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {value}",# ({rate:.2f}% of {total})",
            va="center",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.savefig(
        output_path.with_suffix(".pdf"),
        bbox_inches="tight",
    )
    plt.close()


def plot_stacked_register_success_histogram(
    successes_by_group: dict[Any, Counter[str]],
    output_path: Path,
    title: str,
    group_labels: dict[Any, str] | None = None,
    group_colors: dict[Any, str] | None = None,
    group_order: list[Any] | None = None,
    top_n: int = TOP_N_REGISTERS,
) -> None:
    if not successes_by_group:
        return

    # ---------------------------------------------------------------
    # Calcul du nombre cumulé de succès par registre.
    #
    # Ce total sert uniquement à sélectionner les TOP_N_REGISTERS.
    # Les segments de la barre correspondent ensuite aux différents
    # groupes (stratégies ou modèles de faute).
    # ---------------------------------------------------------------

    total_successes: Counter[str] = Counter()

    for register_counter in successes_by_group.values():
        total_successes.update(register_counter)

    if not total_successes:
        return

    selected_registers = [
        register
        for register, _
        in total_successes.most_common(top_n)
    ]

    # Inversion pour avoir le registre le plus impacté en haut.
    selected_registers = list(reversed(selected_registers))

    figure_height = max(
        5.0,
        0.45 * len(selected_registers)
    )

    fig, ax = plt.subplots(
        figsize=(10, figure_height)
    )

    # Position de départ de chaque segment.
    left = [0] * len(selected_registers)

    if group_order is not None:
        groups = [
            group
            for group in group_order
            if group in successes_by_group
        ]
    else:
        groups = sorted(
            successes_by_group.keys(),
            key=str
        )

    if not groups:
        print(
            f"[Figure ignorée] Aucun groupe disponible pour : {title}"
        )
        return

    for group in groups:
        values = [
            successes_by_group[group][register]
            for register in selected_registers
        ]

        label = (
            group_labels.get(group, str(group))
            if group_labels
            else str(group)
        )

        color = (
            group_colors.get(group)
            if group_colors
            else None
        )

        ax.barh(
            selected_registers,
            values,
            left=left,
            label=label,
            color=color,
        )

        left = [
            current_left + value
            for current_left, value
            in zip(left, values)
        ]

    # ---------------------------------------------------------------
    # Affichage du total au bout de chaque barre.
    # ---------------------------------------------------------------

    for index, register in enumerate(selected_registers):

        total = total_successes[register]

        ax.text(
            total,
            index,
            f" {total}",
            va="center",
            fontsize=8,
        )

    ax.set_xlabel("Number of successful attacks")
    ax.set_ylabel("Faulted register")
    ax.set_title(title)
    ax.set_xlim(left=0)

    ax.legend(
        loc="best",
        fontsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        output_path.with_suffix(".pdf"),
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_pair_histogram(
    rows: list[dict[str, Any]],
    output_path: Path,
    title: str,
    top_n: int = TOP_N_PAIRS,
) -> None:
    if not rows:
        return

    selected_rows = list(reversed(rows[:top_n]))

    labels = [
        row["register_pair"]
        for row in selected_rows
    ]

    values = [
        row["success_rate_percent"]
        for row in selected_rows
    ]

    totals = [
        row["total_simulations"]
        for row in selected_rows
    ]

    successes = [
        row["successful_simulations"]
        for row in selected_rows
    ]

    figure_height = max(5.0, 0.55 * len(selected_rows))

    plt.figure(figsize=(12, figure_height))
    bars = plt.barh(labels, values)

    plt.xlabel("Successful attack rate (%)")
    plt.ylabel("Faulted register pair")
    plt.title(title)
    plt.xlim(left=0)

    for bar, value, success, total in zip(
        bars,
        values,
        successes,
        totals,
    ):
        plt.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {value:.2f}% ({success}/{total})",
            va="center",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.savefig(
        output_path.with_suffix(".pdf"),
        bbox_inches="tight",
    )
    plt.close()


def plot_register_success_rate_by_group(
    successes_by_group: dict[Any, Counter[str]],
    totals_by_group: dict[Any, Counter[str]],
    output_path: Path,
    title: str,
    group_labels: dict[Any, str] | None = None,
    group_colors: dict[Any, str] | None = None,
    group_order: list[Any] | None = None,
    excluded_registers: set[str] | None = None,
    top_n: int = TOP_N_REGISTERS,
) -> None:

    if not successes_by_group or not totals_by_group:
        return

    if excluded_registers is None:
        excluded_registers = set()

    # ---------------------------------------------------------------
    # Ordre des groupes
    # ---------------------------------------------------------------

    if group_order is not None:
        groups = [
            group
            for group in group_order
            if group in totals_by_group
        ]
    else:
        groups = sorted(
            totals_by_group.keys(),
            key=str,
        )

    if not groups:
        print(
            f"[Figure ignorée] Aucun groupe disponible pour : {title}"
        )
        return

    # ---------------------------------------------------------------
    # Pour chaque registre, recherche du groupe ayant le taux de
    # succès maximal.
    #
    # Structure :
    # register -> {
    #     "rate": ...,
    #     "group": ...,
    #     "successes": ...,
    #     "total": ...
    # }
    # ---------------------------------------------------------------

    best_by_register: dict[str, dict[str, Any]] = {}

    for group in groups:

        totals = totals_by_group[group]
        successes = successes_by_group.get(
            group,
            Counter(),
        )

        for register, total in totals.items():

            if register in excluded_registers:
                continue

            # Une combinaison non simulée n'est PAS considérée
            # comme ayant un taux de succès de 0 %.
            if total <= 0:
                continue

            success = successes[register]

            rate = (
                100.0
                * success
                / total
            )

            previous = best_by_register.get(register)

            if (
                previous is None
                or rate > previous["rate"]
            ):
                best_by_register[register] = {
                    "rate": rate,
                    "group": group,
                    "successes": success,
                    "total": total,
                }

    if not best_by_register:
        return

    # ---------------------------------------------------------------
    # Classement selon le taux maximal.
    # En cas d'égalité :
    #   - nombre de succès
    #   - nombre total de simulations
    # ---------------------------------------------------------------

    selected = sorted(
        best_by_register.items(),
        key=lambda item: (
            item[1]["rate"],
            item[1]["successes"],
            item[1]["total"],
        ),
        reverse=True,
    )[:top_n]

    # Inversion pour avoir le plus vulnérable en haut.
    selected = list(reversed(selected))

    labels = [
        register
        for register, _
        in selected
    ]

    values = [
        info["rate"]
        for _, info
        in selected
    ]

    groups_for_registers = [
        info["group"]
        for _, info
        in selected
    ]

    successes = [
        info["successes"]
        for _, info
        in selected
    ]

    totals = [
        info["total"]
        for _, info
        in selected
    ]

    colors = [
        (
            group_colors.get(group)
            if group_colors
            else None
        )
        for group in groups_for_registers
    ]

    figure_height = max(
        5.0,
        0.45 * len(selected)
    )

    fig, ax = plt.subplots(
        figsize=(10, figure_height)
    )

    bars = ax.barh(
        labels,
        values,
        color=colors,
    )

    ax.set_xlabel("Successful attack rate (%)")
    ax.set_ylabel("Faulted register")
    ax.set_title(title)

    # Un peu d'espace pour écrire le pourcentage
    # au bout de chaque barre.
    max_value = max(values)

    if max_value > 0:
        ax.set_xlim(
            0,
            max_value * 1.18,
        )
    else:
        ax.set_xlim(0, 1)

    # ---------------------------------------------------------------
    # Valeur affichée au bout de chaque barre.
    # ---------------------------------------------------------------

    for bar, rate, success, total in zip(
        bars,
        values,
        successes,
        totals,
    ):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {rate:.2f}%",
            va="center",
            fontsize=8,
        )

    # ---------------------------------------------------------------
    # Légende
    # ---------------------------------------------------------------

    represented_groups = set(
        groups_for_registers
    )

    legend_handles = []

    for group in groups:

        if group not in represented_groups:
            continue

        label = (
            group_labels.get(group, str(group))
            if group_labels
            else str(group)
        )

        color = (
            group_colors.get(group)
            if group_colors
            else None
        )

        legend_handles.append(
            Patch(
                facecolor=color,
                label=label,
            )
        )

    if legend_handles:
        ax.legend(
            handles=legend_handles,
            loc="best",
            fontsize=8,
        )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        output_path.with_suffix(".pdf"),
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_register_success_rate_stacked_by_group(
    successes_by_group: dict[Any, Counter[str]],
    totals_by_group: dict[Any, Counter[str]],
    output_path: Path,
    title: str,
    group_labels: dict[Any, str] | None = None,
    group_colors: dict[Any, str] | None = None,
    group_order: list[Any] | None = None,
    excluded_registers: set[str] | None = None,
    top_n: int = TOP_N_REGISTERS,
) -> None:

    if not successes_by_group or not totals_by_group:
        return

    if excluded_registers is None:
        excluded_registers = set()

    # ---------------------------------------------------------------
    # Ordre des groupes
    # ---------------------------------------------------------------

    if group_order is not None:
        groups = [
            group
            for group in group_order
            if group in totals_by_group
        ]
    else:
        groups = sorted(
            totals_by_group.keys(),
            key=str,
        )

    if not groups:
        print(
            f"[Figure ignorée] Aucun groupe disponible pour : {title}"
        )
        return

    # ---------------------------------------------------------------
    # Récupération de tous les registres
    # ---------------------------------------------------------------

    registers = set()

    for group in groups:
        registers.update(
            totals_by_group[group].keys()
        )

    registers -= excluded_registers

    # ---------------------------------------------------------------
    # Calcul du taux GLOBAL de chaque registre.
    #
    # Il sert uniquement à classer les registres pour sélectionner
    # le Top N.
    #
    # global_rate =
    #     somme(successes) / somme(total)
    # ---------------------------------------------------------------

    register_global_rate = {}

    for register in registers:

        total_success = 0
        total_simulations = 0

        for group in groups:

            total = totals_by_group[
                group
            ].get(
                register,
                0,
            )

            success = successes_by_group.get(
                group,
                Counter(),
            ).get(
                register,
                0,
            )

            total_success += success
            total_simulations += total

        if total_simulations > 0:

            register_global_rate[register] = (
                100.0
                * total_success
                / total_simulations
            )

    if not register_global_rate:
        return

    # ---------------------------------------------------------------
    # Top N registres selon le taux global
    # ---------------------------------------------------------------

    selected_registers = [
        register
        for register, _
        in sorted(
            register_global_rate.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:top_n]
    ]

    # barh affiche le premier en bas
    selected_registers = list(
        reversed(selected_registers)
    )

    # ---------------------------------------------------------------
    # Création de la figure
    # ---------------------------------------------------------------

    figure_height = max(
        5.0,
        0.45 * len(selected_registers),
    )

    fig, ax = plt.subplots(
        figsize=(10, figure_height)
    )

    left = [
        0.0
        for _ in selected_registers
    ]

    # ---------------------------------------------------------------
    # Une portion de barre par stratégie / modèle
    # ---------------------------------------------------------------

    for group in groups:

        values = []

        for register in selected_registers:

            total = totals_by_group[
                group
            ].get(
                register,
                0,
            )

            success = successes_by_group.get(
                group,
                Counter(),
            ).get(
                register,
                0,
            )

            if total > 0:
                rate = (
                    100.0
                    * success
                    / total
                )
            else:
                # Non simulé :
                # pas de contribution à la barre.
                rate = 0.0

            values.append(rate)

        label = (
            group_labels.get(
                group,
                str(group),
            )
            if group_labels
            else str(group)
        )

        color = (
            group_colors.get(group)
            if group_colors
            else None
        )

        bars = ax.barh(
            selected_registers,
            values,
            left=left,
            label=label,
            color=color,
        )

        # -----------------------------------------------------------
        # Affichage du pourcentage dans chaque portion
        # suffisamment grande.
        # -----------------------------------------------------------

        for bar, value in zip(
            bars,
            values,
        ):

            if value <= 0:
                continue

            # On évite d'écrire du texte dans les portions
            # extrêmement petites.
            if value >= 0.50:
                ax.text(
                    bar.get_x()
                    + bar.get_width() / 2,
                    bar.get_y()
                    + bar.get_height() / 2,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=7,
                )

        left = [
            current_left + value
            for current_left, value
            in zip(left, values)
        ]

    # ---------------------------------------------------------------
    # Mise en forme
    # ---------------------------------------------------------------

    ax.set_xlabel(
        "Successful attack rate (%)"
    )

    ax.set_ylabel(
        "Faulted register"
    )

    ax.set_title(
        title
    )

    ax.legend(
        loc="best",
        fontsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        output_path.with_suffix(".pdf"),
        bbox_inches="tight",
    )

    plt.close(fig)

# ---------------------------------------------------------------------------
# Sauvegarde d'un groupe de résultats
# ---------------------------------------------------------------------------
def save_statistics(
    name: str,
    statistics: Statistics,
    title: str,
) -> None:
    directory_name = safe_filename(name)
    output_directory = OUTPUT_DIRECTORY / directory_name
    output_directory.mkdir(parents=True, exist_ok=True)

    register_rows = build_register_rows(statistics)
    pair_rows = build_pair_rows(statistics)

    write_csv(
        output_directory / "register_sensitivity.csv",
        register_rows,
    )

    write_csv(
        output_directory / "register_pair_sensitivity.csv",
        pair_rows,
    )

    write_summary_file(
        output_directory / "summary.txt",
        statistics,
    )

    if title == "buffer_overflow":
        title = "Buffer Overflow"
    elif title == "secretFunction":
        title = "Format String"
        
    plot_register_histogram(
        register_rows,
        output_directory / "top_registers.png",
        f"Most vulnerable registers — {title}",
    )

    plot_register_success_histogram(
        register_rows,
        output_directory / "top_registers_successes.png",
        f"Registers with the highest number of successful attacks — {title}",
    )

    plot_pair_histogram(
        pair_rows,
        output_directory / "top_register_pairs.png",
        f"Most vulnerable register pairs — {title}",
    )


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------
def main() -> None:
    root_directory = find_root_directory()

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    global_statistics = Statistics.create()

    statistics_by_use_case: dict[str, Statistics] = defaultdict(
        Statistics.create
    )

    statistics_by_campaign: dict[
        tuple[str, str, int, str],
        Statistics,
    ] = defaultdict(Statistics.create)

    # Succès par registre, séparés par stratégie.
    register_success_by_use_case_strategy: dict[
        str,
        dict[int, Counter[str]],
    ] = defaultdict(
        lambda: defaultdict(Counter)
    )

    # Succès par registre, séparés par modèle de faute.
    register_success_by_use_case_fault_model: dict[
        str,
        dict[str, Counter[str]],
    ] = defaultdict(
        lambda: defaultdict(Counter)
    )

    register_total_by_use_case_strategy: dict[
        str,
        dict[int, Counter[str]],
    ] = defaultdict(
        lambda: defaultdict(Counter)
    )

    register_total_by_use_case_fault_model: dict[
        str,
        dict[str, Counter[str]],
    ] = defaultdict(
        lambda: defaultdict(Counter)
    )

    register_success_detailed = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(Counter)
            )
        )
    )

    register_total_detailed = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(Counter)
            )
        )
    )

    register_names_by_strategy: dict[
        tuple[int, str],
        set[str],
    ] = defaultdict(set)

    aliases = load_register_aliases(
        REGISTER_ALIASES_FILE
    )

    print(f"Alias chargés : {len(aliases)}")

    json_file_count = 0
    campaign_count = 0
    invalid_folder_count = 0

    print(f"Dossier analysé : {root_directory.resolve()}")
    print()

    for use_case_directory in sorted(root_directory.iterdir()):
        if not use_case_directory.is_dir():
            continue

        use_case = use_case_directory.name

        for campaign_directory in sorted(use_case_directory.iterdir()):
            if not campaign_directory.is_dir():
                continue

            metadata = parse_campaign_folder(
                campaign_directory,
                use_case,
            )

            if metadata is None:
                print(
                    "[Dossier ignoré : nom non reconnu] "
                    f"{campaign_directory}"
                )
                invalid_folder_count += 1
                continue

            campaign_count += 1

            campaign_key = (
                metadata.use_case,
                metadata.protection,
                metadata.strategy,
                metadata.fault_model,
            )

            json_files = sorted(
                campaign_directory.rglob("*.json")
            )

            print(
                f"[{metadata.use_case}] "
                f"{metadata.protection}, "
                f"stratégie {metadata.strategy}, "
                f"{metadata.fault_model}: "
                f"{len(json_files)} fichier(s)"
            )

            for json_path in json_files:
                file_statistics = analyse_json_file(
                    json_path=json_path,
                    strategy=metadata.strategy,
                    protection=metadata.protection,
                    aliases=aliases,
                )

                json_file_count += 1

                global_statistics.merge(file_statistics)
                statistics_by_use_case[metadata.use_case].merge(
                    file_statistics
                )
                statistics_by_campaign[campaign_key].merge(
                    file_statistics
                )

                # ---------------------------------------------------------------
                # Répartition des succès par stratégie.
                # ---------------------------------------------------------------
                register_success_by_use_case_strategy[
                    metadata.use_case
                ][
                    metadata.strategy
                ].update(
                    file_statistics.register_success
                )

                # ---------------------------------------------------------------
                # Répartition des succès par modèle de faute.
                # ---------------------------------------------------------------
                register_success_by_use_case_fault_model[
                    metadata.use_case
                ][
                    metadata.fault_model
                ].update(
                    file_statistics.register_success
                )

                # ---------------------------------------------------------------
                register_total_by_use_case_strategy[
                    metadata.use_case
                ][
                    metadata.strategy
                ].update(
                    file_statistics.register_total
                )

                register_total_by_use_case_fault_model[
                    metadata.use_case
                ][
                    metadata.fault_model
                ].update(
                    file_statistics.register_total
                )

                ###############################################################
                register_success_detailed[
                    metadata.use_case
                ][
                    metadata.protection
                ][
                    metadata.strategy
                ][
                    metadata.fault_model
                ].update(
                    file_statistics.register_success
                )

                register_total_detailed[
                    metadata.use_case
                ][
                    metadata.protection
                ][
                    metadata.strategy
                ][
                    metadata.fault_model
                ].update(
                    file_statistics.register_total
                )

                # register_names_by_strategy[
                #     (
                #         metadata.strategy,
                #         metadata.protection,
                #     )
                # ].update(
                #     file_statistics.register_total.keys()
                # )

    # Résultats globaux
    save_statistics(
        name="global",
        statistics=global_statistics,
        title="all campaigns",
    )

    # Résultats par cas d'usage
    for use_case, statistics in statistics_by_use_case.items():
        save_statistics(
            name=f"use_case_{use_case}",
            statistics=statistics,
            title=use_case,
        )

    # ------------------------------------------------------------------
    # Histogrammes empilés par stratégie
    # ------------------------------------------------------------------
    for use_case, grouped_data in (
        register_success_by_use_case_strategy.items()
    ):

        output_directory = (
            OUTPUT_DIRECTORY
            / f"use_case_{safe_filename(use_case)}"
        )

        if use_case == "buffer_overflow":
            display_name = "Buffer Overflow"
            use_case_suffix = "bo"

        elif use_case == "secretFunction":
            display_name = "Format String"
            use_case_suffix = "fs"

        else:
            display_name = use_case
            use_case_suffix = safe_filename(use_case)

        strategy_labels = {
            strategy: f"Strategy {strategy}"
            for strategy in grouped_data
        }

        plot_stacked_register_success_histogram(
            successes_by_group=grouped_data,
            output_path=(
                output_directory
                / f"top_registers_successes_by_strategy_{use_case_suffix}.png"
            ),
            title=(
                "Successful attacks by strategy — "
                f"{display_name}"
            ),
            group_labels=strategy_labels,
            group_colors=STRATEGY_COLORS,
            group_order=[1, 2, 3, 4, 5],
        )

    # ------------------------------------------------------------------
    # Histogrammes empilés par modèle de faute
    # ------------------------------------------------------------------
    for use_case, grouped_data in (
        register_success_by_use_case_fault_model.items()
    ):
        output_directory = (
            OUTPUT_DIRECTORY
            / f"use_case_{safe_filename(use_case)}"
        )

        if use_case == "buffer_overflow":
            display_name = "Buffer Overflow"
            use_case_suffix = "bo"

        elif use_case == "secretFunction":
            display_name = "Format String"
            use_case_suffix = "fs"

        else:
            display_name = use_case
            use_case_suffix = safe_filename(use_case)

        fault_model_labels = {
            fault_model: format_fault_model_name(fault_model)
            for fault_model in grouped_data
        }

        plot_stacked_register_success_histogram(
            successes_by_group=grouped_data,
            output_path=(
                output_directory
                / f"top_registers_successes_by_fault_model_{use_case_suffix}.png"
            ),
            title=(
                "Successful attacks by fault model — "
                f"{display_name}"
            ),
            group_labels=fault_model_labels,
            group_colors=FAULT_MODEL_COLORS,
            group_order=FAULT_MODEL_ORDER,
        )

    # ------------------------------------------------------------------
    # Success rate par stratégie
    # ------------------------------------------------------------------
    for use_case, grouped_successes in (
        register_success_by_use_case_strategy.items()
    ):

        grouped_totals = (
            register_total_by_use_case_strategy[
                use_case
            ]
        )

        output_directory = (
            OUTPUT_DIRECTORY
            / f"use_case_{safe_filename(use_case)}"
        )

        if use_case == "buffer_overflow":
            display_name = "Buffer Overflow"
            use_case_suffix = "bo"

        elif use_case == "secretFunction":
            display_name = "Format String"
            use_case_suffix = "fs"

        else:
            display_name = use_case
            use_case_suffix = safe_filename(use_case)

        strategy_labels = {
            strategy: f"Strategy {strategy}"
            for strategy in STRATEGY_ORDER
        }

        plot_register_success_rate_stacked_by_group(
            successes_by_group=grouped_successes,
            totals_by_group=grouped_totals,
            output_path=(
                output_directory
                / f"top_registers_success_rate_by_strategy_{use_case_suffix}.png"
            ),
            title=(
                "Successful attack rate by strategy — "
                f"{display_name}"
            ),
            group_labels=strategy_labels,
            group_colors=STRATEGY_COLORS,
            group_order=STRATEGY_ORDER,
        )

    # ------------------------------------------------------------------
    # Success rate par modèle de faute
    # ------------------------------------------------------------------
    for use_case, grouped_successes in (
        register_success_by_use_case_fault_model.items()
    ):

        grouped_totals = (
            register_total_by_use_case_fault_model[
                use_case
            ]
        )

        output_directory = (
            OUTPUT_DIRECTORY
            / f"use_case_{safe_filename(use_case)}"
        )

        if use_case == "buffer_overflow":
            display_name = "Buffer Overflow"
            use_case_suffix = "bo"

        elif use_case == "secretFunction":
            display_name = "Format String"
            use_case_suffix = "fs"

        else:
            display_name = use_case
            use_case_suffix = safe_filename(use_case)

        fault_model_labels = {
            fault_model:
                format_fault_model_name(fault_model)
            for fault_model in FAULT_MODEL_ORDER
        }

        plot_register_success_rate_stacked_by_group(
            successes_by_group=grouped_successes,
            totals_by_group=grouped_totals,
            output_path=(
                output_directory
                / f"top_registers_success_rate_by_fault_model_{use_case_suffix}.png"
            ),
            title=(
                "Successful attack rate by fault model — "
                f"{display_name}"
            ),
            group_labels=fault_model_labels,
            group_colors=FAULT_MODEL_COLORS,
            group_order=FAULT_MODEL_ORDER,

            # Non comparables entre les trois modèles
            # excluded_registers={
            #     "tpr_q",
            #     "tcr_q",
            # },
        )

    # Résultats par campagne
    for campaign_key, statistics in statistics_by_campaign.items():
        use_case, protection, strategy, fault_model = campaign_key

        name = (
            f"{use_case}_"
            f"{protection}_"
            f"strategy_{strategy}_"
            f"{fault_model}"
        )

        title = (
            f"{use_case}, {protection}, "
            f"strategy {strategy}, {fault_model}"
        )

        save_statistics(
            name=name,
            statistics=statistics,
            title=title,
        )

    # write_register_alias_template(
    #     Path("register_aliases_template.csv"),
    #     register_names_by_strategy,
    # )

    export_register_statistics_csv(
        register_success_detailed,
        register_total_detailed,
        OUTPUT_DIRECTORY / "register_statistics_csv",
    )

    print()
    print("Analyse terminée.")
    print(f"Campagnes détectées : {campaign_count}")
    
    # print("Modèle d'alias généré dans : "
    #       f"{Path('register_aliases_template.csv').resolve()}"
    # )
    print(f"Fichiers JSON analysés : {json_file_count}")
    print(
        "Simulations fautées analysées : "
        f"{global_statistics.simulations}"
    )
    print(
        "Simulations réussies : "
        f"{global_statistics.successful_simulations}"
    )

    if global_statistics.simulations:
        success_rate = (
            100.0
            * global_statistics.successful_simulations
            / global_statistics.simulations
        )

        print(f"Taux de succès global : {success_rate:.6f}%")

    if invalid_folder_count:
        print(
            "Dossiers ignorés à cause de leur nom : "
            f"{invalid_folder_count}"
        )

    print(
        "Résultats enregistrés dans : "
        f"{OUTPUT_DIRECTORY.resolve()}"
    )


if __name__ == "__main__":
    main()