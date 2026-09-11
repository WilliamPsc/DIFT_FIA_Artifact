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
├── attacks/
│   ├── buffer_overflow/
│   └── format_string/
│
├── fault_injection/
│   ├── configurations/
│   └── scripts/
│
├── countermeasures/
│   ├── parity/
│   ├── hamming/
│   └── secded/
│
└── analysis/
    ├── scripts/
    └── register_aliases.csv
```

The exact content of each directory is described in the corresponding sections below.

## Fault Models

Three fault models are considered in the experiments. For each campaign, the considered injection are explored over the attack execution window (few clock cycles).

- **Fault Model 1 — Single-bit faults in two registers**: A single bit is faulted in two registers during the same clock cycle. 

- **Fault Model 2 — Multi-bit faults in one register**: Multiple bits of a single register are faulted during the same clock cycle.

- **Fault Model 3 — Multi-bit faults in two registers**: Multiple bits distributed over two different registers are faulted during the same clock cycle.

## Protection Strategies

This repository contains the implementations and/or configurations associated with the five protection strategies described in the paper.

The strategies progressively modify the granularity at which the DIFT registers are protected, from groups of registers to fine-grained protection. Please refer to the paper for the complete description of the five strategies and their hardware organisation.

## Fault Injection Campaigns

Fault injection campaigns are performed using [FISSA](https://github.com/WilliamPsc/FISSA) (Fault Injection Simulation for Security Assessment). FISSA automates fault injection experiments at RTL simulation level and generates the simulation campaigns used in this work.

Each simulation targets a single clock cycle and one or two registers, depending on the considered fault model. The campaigns repeat the experiment over the considered clock cycles and targeted registers.

## Result Analysis

We do not provide the analysis scripts from FISSA. You can find them in the FISSA repository. We only provide the scripts used to generate the register sensitivity from the paper. Some scripts are generated using the help of ChatGPT 5.6-Sol. 

The register_aliases.csv file maps RTL hierarchical register names to shorter names used in the analysis and figures.

### Reproducing the Experiments

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
  author  = {William PENSEC, Francesco REGAZZONI, Vianney LAPÔTRE, Guy GOGNIAT},
  journal = {TODO},
  year    = {2026}
}
```
The complete bibliographic information will be added after publication.

## License

The original code provided as part of this artifact is distributed under
the terms specified in the ```LICENSE``` file.

Third-party components remain subject to their respective licenses.