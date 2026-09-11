# Artifact for "Comparative Evaluation of Redundancy-Based Hardware Countermeasures for Enhancing DIFT Resilience Against Fault Injection Attacks"

This repository provides the experimental artifact associated with the paper:

> **Comparative Evaluation of Redundancy-Based Hardware Countermeasures for Enhancing DIFT Resilience Against Fault Injection Attacks**

The artifact contains the material used to evaluate the resilience of the D-RI5CY processor against fault injection attacks and the proposed redundancy-based hardware countermeasures.

## Overview

[D-RI5CY](https://github.com/sld-columbia/riscv-dift) extends the [RI5CY](https://github.com/embecosm/ri5cy) RISC-V processor with a hardware Dynamic Information Flow Tracking (DIFT) mechanism. Security tags are propagated alongside data during program execution and checked according to a configurable security policy.

This work evaluates the resilience of the DIFT mechanism against fault injection attacks and investigates several hardware protection strategies based on:

- Simple parity;
- Hamming Code;
- SECDED (Single Error Correction, Double Error Detection).

Five protection implementation strategies with different protection granularities are evaluated.

The experiments consider two software attack scenarios:

- Buffer Overflow;
- Format String.

The fault injection campaigns are performed using [FISSA](https://github.com/WilliamPsc/FISSA) (Fault Injection Simulation for Security Assessment).

## Repository Structure

The repository is organised as follows:

```text
.
├── README.md
├── LICENSE
│
├── fault_injections/
│   ├── configurations/
│   └── registers/
│
├── countermeasures/
│   ├── parity/
│   ├── hamming_code/
│   └── secded/
│
└── analysis/
    ├── baseline_vs_secded5_results/
    ├── register_sensitivity_results/
    ├── full_analysis.py
    ├── analyse_baseline_sd5.py
    └── register_aliases.csv
```

The exact content of each directory is described in the corresponding sections below.

## Countermeasures

This repository contains the implementations and/or configurations associated with the five protection strategies described in the paper.

The strategies progressively modify the granularity at which the DIFT registers are protected, from groups of registers to fine-grained protection. Please refer to the paper for the complete description of the five strategies and their hardware organisation. [Five tables](#registers) are given below to show the details of the different groups for the five strategies

## Fault Injection Campaigns

Fault injection campaigns are performed using [FISSA](https://github.com/WilliamPsc/FISSA) (Fault Injection Simulation for Security Assessment). FISSA automates fault injection experiments at RTL simulation level and generates the simulation campaigns used in this work.

Each simulation targets a single clock cycle and one or two registers, depending on the considered fault model. The campaigns repeat the experiment over the considered clock cycles and targeted registers.

### Configurations

In the `fault_injections/configurations` folder, the configuration files used to generate the fault injection campaigns are provided. For Strategies 2 to 5 using Hamming Code or SECDED, only the version parameter needs to be changed:

```json
"version": 1,
```

By default, the `version` parameter is set to Strategy 1 and can be changed to a value ranging from 1 to 5.

#### Fault Models

Three fault models are considered in the experiments. For each campaign, fault injections are explored over the complete attack execution window, which consists of a few clock cycles:

- **Fault Model 1 — Single-bit faults in two registers**: A single bit is faulted in two registers during the same clock cycle. 

- **Fault Model 2 — Multi-bit faults in one register**: Multiple bits of a single register are faulted during the same clock cycle.

- **Fault Model 3 — Multi-bit faults in two registers**: Multiple bits distributed over two different registers are faulted during the same clock cycle.

### Registers

In the`fault_injections/registers`folder contains the files defining the DIFT-related registers targeted by the fault injection campaigns for each protection strategy. These files include the original D-RI5CY DIFT-related registers as well as the protection-related registers introduced by simple parity, Hamming Code, or SECDED. For Hamming Code and SECDED, five register configuration files are provided, corresponding to the five protection strategies.

The five strategies group the DIFT-related registers differently, each with a specific objective:

|                |                   **Objective**                   |
| :------------: | :-----------------------------------------------: |
| **Strategy 1** |             Minimize redundancy bits              |
| **Strategy 2** |              Protect pipeline stage               |
| **Strategy 3** |              Protect every register               |
| **Strategy 4** | Individual protection and reinforce CSR registers |
| **Strategy 5** |          Split registers across encoders          |

The rationale behind the register grouping adopted by each strategy is detailed in the paper.

#### Strategy 1:

|      **Register Name**       |          **Module**          | **Size** | **Group** |
| :--------------------------: | :--------------------------: | :------: | :-------: |
|        `pc_id_o_tag`         |   Instruction Fetch Stage    |    1     |    Gr5    |
|        `pc_if_o_tag`         |   Instruction Fetch Stage    |    1     |    Gr5    |
|   `alu_operand_a_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr5    |
|   `alu_operand_b_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr5    |
|   `alu_operand_c_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr5    |
|    `alu_operator_o_mode`     |   Instruction Decode Stage   |    2     |    Gr5    |
|       `check_d_o_tag`        |   Instruction Decode Stage   |    1     |    Gr5    |
|       `check_s1_o_tag`       |   Instruction Decode Stage   |    1     |    Gr5    |
|       `check_s2_o_tag`       |   Instruction Decode Stage   |    1     |    Gr5    |
|    `is_store_post_o_tag`     |   Instruction Decode Stage   |    1     |    Gr5    |
|      `memory_set_o_tag`      |   Instruction Decode Stage   |    1     |    Gr5    |
| `regfile_alu_waddr_ex_o_tag` |   Instruction Decode Stage   |    5     |    Gr4    |
|     `register_set_o_tag`     |   Instruction Decode Stage   |    1     |    Gr5    |
|  `store_dest_addr_ex_o_tag`  |   Instruction Decode Stage   |    1     |    Gr5    |
|   `store_source_ex_o_tag`    |   Instruction Decode Stage   |    1     |    Gr5    |
|     `use_store_ops_ex_o`     |   Instruction Decode Stage   |    1     |    Gr5    |
|        `rf_reg[31:0]`        |      Register File Tag       |   32x1   |    Gr3    |
|         `rs1_o_tag`          |        Execute Stage         |    1     |    Gr5    |
|           `tcr_q`            | Control and Status Registers |    32    |    Gr1    |
|           `tpr_q`            | Control and Status Registers |    32    |    Gr2    |
|      `data_type_q_tag`       |       Load/Store Unit        |    2     |    Gr5    |
|       `data_we_q_tag`        |       Load/Store Unit        |    1     |    Gr5    |
|     `rdata_offset_q_tag`     |       Load/Store Unit        |    2     |    Gr5    |
|        `rdata_q_tag`         |       Load/Store Unit        |    4     |    Gr5    |

#### Strategy 2:

|      **Register Name**       |          **Module**          | **Size** | **Group** |
| :--------------------------: | :--------------------------: | :------: | :-------: |
|        `pc_id_o_tag`         |   Instruction Fetch Stage    |    1     |    Gr1    |
|        `pc_if_o_tag`         |   Instruction Fetch Stage    |    1     |    Gr1    |
|   `alu_operand_a_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr2    |
|   `alu_operand_b_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr2    |
|   `alu_operand_c_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr2    |
|    `alu_operator_o_mode`     |   Instruction Decode Stage   |    2     |    Gr2    |
|       `check_d_o_tag`        |   Instruction Decode Stage   |    1     |    Gr2    |
|       `check_s1_o_tag`       |   Instruction Decode Stage   |    1     |    Gr2    |
|       `check_s2_o_tag`       |   Instruction Decode Stage   |    1     |    Gr2    |
|    `is_store_post_o_tag`     |   Instruction Decode Stage   |    1     |    Gr2    |
|      `memory_set_o_tag`      |   Instruction Decode Stage   |    1     |    Gr2    |
| `regfile_alu_waddr_ex_o_tag` |   Instruction Decode Stage   |    5     |    Gr2    |
|     `register_set_o_tag`     |   Instruction Decode Stage   |    1     |    Gr2    |
|  `store_dest_addr_ex_o_tag`  |   Instruction Decode Stage   |    1     |    Gr2    |
|   `store_source_ex_o_tag`    |   Instruction Decode Stage   |    1     |    Gr2    |
|     `use_store_ops_ex_o`     |   Instruction Decode Stage   |    1     |    Gr2    |
|        `rf_reg[31:0]`        |      Register File Tag       |   32x1   |    Gr3    |
|         `rs1_o_tag`          |        Execute Stage         |    1     |    Gr4    |
|           `tcr_q`            | Control and Status Registers |    32    |    Gr5    |
|           `tpr_q`            | Control and Status Registers |    32    |    Gr6    |
|      `data_type_q_tag`       |       Load/Store Unit        |    2     |    Gr7    |
|       `data_we_q_tag`        |       Load/Store Unit        |    1     |    Gr7    |
|     `rdata_offset_q_tag`     |       Load/Store Unit        |    2     |    Gr7    |
|        `rdata_q_tag`         |       Load/Store Unit        |    4     |    Gr7    |

#### Strategy 3:

|      **Register Name**       |          **Module**          | **Size** | **Group** |
| :--------------------------: | :--------------------------: | :------: | :-------: |
|        `pc_if_o_tag`         |   Instruction Fetch Stage    |    1     |    Gr1    |
|        `pc_id_o_tag`         |   Instruction Fetch Stage    |    1     |    Gr2    |
|   `alu_operand_a_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr3    |
|   `alu_operand_b_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr4    |
|   `alu_operand_c_ex_o_tag`   |   Instruction Decode Stage   |    1     |    Gr5    |
|    `alu_operator_o_mode`     |   Instruction Decode Stage   |    2     |    Gr6    |
|       `check_d_o_tag`        |   Instruction Decode Stage   |    1     |    Gr7    |
|       `check_s1_o_tag`       |   Instruction Decode Stage   |    1     |    Gr8    |
|       `check_s2_o_tag`       |   Instruction Decode Stage   |    1     |    Gr9    |
|    `is_store_post_o_tag`     |   Instruction Decode Stage   |    1     |   Gr10    |
|      `memory_set_o_tag`      |   Instruction Decode Stage   |    1     |   Gr11    |
| `regfile_alu_waddr_ex_o_tag` |   Instruction Decode Stage   |    5     |   Gr12    |
|     `register_set_o_tag`     |   Instruction Decode Stage   |    1     |   Gr13    |
|  `store_dest_addr_ex_o_tag`  |   Instruction Decode Stage   |    1     |   Gr14    |
|   `store_source_ex_o_tag`    |   Instruction Decode Stage   |    1     |   Gr15    |
|     `use_store_ops_ex_o`     |   Instruction Decode Stage   |    1     |   Gr16    |
|        `rf_reg[31:0]`        |      Register File Tag       |   32x1   |   Gr17    |
|         `rs1_o_tag`          |        Execute Stage         |    1     |   Gr18    |
|           `tcr_q`            | Control and Status Registers |    32    |   Gr19    |
|           `tpr_q`            | Control and Status Registers |    32    |   Gr20    |
|      `data_type_q_tag`       |       Load/Store Unit        |    2     |   Gr21    |
|       `data_we_q_tag`        |       Load/Store Unit        |    1     |   Gr22    |
|     `rdata_offset_q_tag`     |       Load/Store Unit        |    2     |   Gr23    |
|        `rdata_q_tag`         |       Load/Store Unit        |    4     |   Gr24    |

#### Strategy 4:

|      **Register Name**       |          **Module**          | **Size** |  **Group**   |
| :--------------------------: | :--------------------------: | :------: | :----------: |
|        `pc_if_o_tag`         |   Instruction Fetch Stage    |    1     |     Gr1      |
|        `pc_id_o_tag`         |   Instruction Fetch Stage    |    1     |     Gr2      |
|   `alu_operand_a_ex_o_tag`   |   Instruction Decode Stage   |    1     |     Gr3      |
|   `alu_operand_b_ex_o_tag`   |   Instruction Decode Stage   |    1     |     Gr4      |
|   `alu_operand_c_ex_o_tag`   |   Instruction Decode Stage   |    1     |     Gr5      |
|    `alu_operator_o_mode`     |   Instruction Decode Stage   |    2     |     Gr6      |
|       `check_d_o_tag`        |   Instruction Decode Stage   |    1     |     Gr7      |
|       `check_s1_o_tag`       |   Instruction Decode Stage   |    1     |     Gr8      |
|       `check_s2_o_tag`       |   Instruction Decode Stage   |    1     |     Gr9      |
|    `is_store_post_o_tag`     |   Instruction Decode Stage   |    1     |     Gr10     |
|      `memory_set_o_tag`      |   Instruction Decode Stage   |    1     |     Gr11     |
| `regfile_alu_waddr_ex_o_tag` |   Instruction Decode Stage   |    5     |     Gr12     |
|     `register_set_o_tag`     |   Instruction Decode Stage   |    1     |     Gr13     |
|  `store_dest_addr_ex_o_tag`  |   Instruction Decode Stage   |    1     |     Gr14     |
|   `store_source_ex_o_tag`    |   Instruction Decode Stage   |    1     |     Gr15     |
|     `use_store_ops_ex_o`     |   Instruction Decode Stage   |    1     |     Gr16     |
|        `rf_reg[31:0]`        |      Register File Tag       |   32x1   |     Gr17     |
|         `rs1_o_tag`          |        Execute Stage         |    1     |     Gr18     |
|           `tpr_q`            | Control and Status Registers |    32    | Gr19 -- Gr26 |
|           `tcr_q`            | Control and Status Registers |    32    | Gr27 -- Gr34 |
|      `data_type_q_tag`       |       Load/Store Unit        |    2     |     Gr35     |
|       `data_we_q_tag`        |       Load/Store Unit        |    1     |     Gr36     |
|     `rdata_offset_q_tag`     |       Load/Store Unit        |    2     |     Gr37     |
|        `rdata_q_tag`         |       Load/Store Unit        |    4     |     Gr38     |

#### Strategy 5:

|      **Register Name**       |          **Module**          | **Size** |          **Group**          |
| :--------------------------: | :--------------------------: | :------: | :-------------------------: |
|        `pc_if_o_tag`         |   Instruction Fetch Stage    |    1     |             Gr1             |
|        `pc_id_o_tag`         |   Instruction Fetch Stage    |    1     |             Gr1             |
|   `alu_operand_a_ex_o_tag`   |   Instruction Decode Stage   |    1     |             Gr4             |
|   `alu_operand_b_ex_o_tag`   |   Instruction Decode Stage   |    1     |             Gr5             |
|   `alu_operand_c_ex_o_tag`   |   Instruction Decode Stage   |    1     |             Gr6             |
|    `alu_operator_o_mode`     |   Instruction Decode Stage   |    2     |         Gr2 -- Gr3          |
|       `check_d_o_tag`        |   Instruction Decode Stage   |    1     |             Gr9             |
|       `check_s1_o_tag`       |   Instruction Decode Stage   |    1     |             Gr7             |
|       `check_s2_o_tag`       |   Instruction Decode Stage   |    1     |             Gr8             |
|    `is_store_post_o_tag`     |   Instruction Decode Stage   |    1     |            Gr10             |
|      `memory_set_o_tag`      |   Instruction Decode Stage   |    1     |            Gr11             |
| `regfile_alu_waddr_ex_o_tag` |   Instruction Decode Stage   |    5     |         Gr5 -- Gr9          |
|     `register_set_o_tag`     |   Instruction Decode Stage   |    1     |            Gr10             |
|  `store_dest_addr_ex_o_tag`  |   Instruction Decode Stage   |    1     |             Gr2             |
|   `store_source_ex_o_tag`    |   Instruction Decode Stage   |    1     |             Gr3             |
|     `use_store_ops_ex_o`     |   Instruction Decode Stage   |    1     |             Gr4             |
|        `rf_reg[31:0]`        |      Register File Tag       |   32x1   |            Gr12             |
|         `rs1_o_tag`          |        Execute Stage         |    1     |            Gr35             |
|           `tpr_q`            | Control and Status Registers |    32    | Gr13 -- Gr26 / Gr28 -- Gr30 |
|           `tcr_q`            | Control and Status Registers |    32    |        Gr13 -- Gr34         |
|      `data_type_q_tag`       |       Load/Store Unit        |    2     |        Gr36 -- Gr37         |
|       `data_we_q_tag`        |       Load/Store Unit        |    1     |            Gr39             |
|     `rdata_offset_q_tag`     |       Load/Store Unit        |    2     |        Gr37 -- Gr38         |
|        `rdata_q_tag`         |       Load/Store Unit        |    4     | Gr35 -- Gr36 / Gr38 -- Gr39 |

## Result Analysis

We do not provide the analysis scripts included in FISSA, as they are already available in the FISSA repository. This artifact only provides the scripts used to perform the register sensitivity analysis presented in the paper. The `register_aliases.csv` file maps hierarchical RTL register names to the shorter names used in the analysis and figures.

### Reproducing the Experiments

The general workflow is:
1) Prepare the D-RI5CY RTL design and the selected protection strategy.
2) Compile the software attack scenario.
3) Configure the fault model and injection campaign.
4) Run the RTL simulations using FISSA and QuestaSim.
5) Collect the generated JSON result files.
6) Run the analysis scripts.
7) Generate the statistics and figures.

## Requirements
The experiments rely on the following main tools:
- FISSA;
- QuestaSim;
- Python 3;
- a RISC-V compilation toolchain.

Note: QuestaSim is proprietary software and is therefore not distributed with this artifact.

## Relationship with the Paper

This artifact is intended to support the reproducibility of the experimental results presented in the paper.

The provided scripts and experimental data correspond to the fault models, countermeasures, and protection strategies described in the manuscript.

## Limitations

Some components used by the experiments may depend on third-party projects or proprietary software and cannot necessarily be redistributed directly with this repository. When applicable, instructions are provided to obtain these dependencies
from their original sources.

## Citation

If you use this artifact in academic work, please cite the associated paper:
```bibtex
@article{PRLG-26-journal,
  title   = {Comparative Evaluation of Redundancy-Based Hardware Countermeasures for Enhancing DIFT Resilience Against Fault Injection Attacks},
  author = {Pensec, William and Regazzoni, Francesco and Lapôtre, Vianney and Gogniat, Guy},
  journal = {TODO},
  year    = {2026}
}
```
The complete bibliographic information will be added after publication.

## License

The original code provided as part of this artifact is distributed under
the terms specified in the ```LICENSE``` file.

Third-party components remain subject to their respective licenses.