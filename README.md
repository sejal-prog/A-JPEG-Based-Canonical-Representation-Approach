# How High-Frequency Image Components Affect Generation Quality
## A JPEG-Based Canonical Representation Approach

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Master's Project at Albert-Ludwigs-Universität Freiburg  
> Computer Vision Group | Supervised by Arian Mousakhan

---

## 📋 Overview

This research investigates how high-frequency image components impact generation quality in two-stage generative models (VQGANs). By replacing learned tokenizers with deterministic JPEG compression, we demonstrate that aggressive frequency removal maintains generation performance despite reconstruction degradation.

### Key Findings
- **FID Scores:** QF=20 (42.78) vs QF=40 (43.96) vs Baseline (43.92)
- **Stable Generation:** High-frequency loss doesn't degrade semantic understanding
- **Training Stability:** JPEG preprocessing eliminates codebook collapse

---

## ⚠️ Code Availability

**The complete implementation is not publicly available** due to:
- Proprietary research agreements
- Institutional privacy policies

This repository contains **preliminary JPEG compression utilities only**.

---

## 📦 Available Components

```
├── DCT_JPG.py              # JPEG DCT compression
├── compression.py          # Compression pipeline
├── huffman_parser.py       # Huffman coding utilities
├── quant.py                # Quantization analysis
└── output/                 # Sample outputs
```

---
Report - https://drive.google.com/file/d/11o6W0CFiWkaqf2uq4OGQDJObHr4CbU_n/view?usp=sharing
The report includes:
- Complete methodology
- VQGAN+DINO architecture details
- Transformer training procedures
- Comprehensive experimental results
- Visual comparisons

---

## 🛠️ Requirements

```bash
pip install numpy opencv-python pillow
```

For full implementation (from report):
- PyTorch 2.0+
- timm (Vision Transformer)
- LPIPS, FID metrics
- BDD100K dataset

---

## 📊 Results Summary

| Method | Embedding | FID ↓ | rFID ↓ |
|--------|-----------|-------|--------|
| VQGAN | 32-dim | 40.66 | 20.53 |
| VQGAN | 16-dim | **43.92** | **19.62** |
| JPEG (QF=40) | 16-dim | 43.96 | 21.85 |
| JPEG (QF=20) | 16-dim | **42.78** | 21.92 |

---

## 🎓 Citation

```bibtex
@mastersthesis{jadhav2025jpeg,
  title={How High-Frequency Image Components Affect Generation Quality: 
         A JPEG-Based Canonical Representation Approach},
  author={Jadhav, Sejal},
  year={2025},
  school={Albert-Ludwigs-Universit{\"a}t Freiburg},
  type={Master's Project}
}
```

---

## 📧 Contact

**Sejal Jadhav**  
**Supervisor:** Arian Mousakhan  
**Examiner:** Prof. Dr. Thomas Brox

---

## 🔗 Related Work

- [VQGAN Paper](https://arxiv.org/abs/2012.09841) - Esser et al., 2021
- [DINO](https://arxiv.org/abs/2104.14294) - Caron et al., 2021
- [BDD100K Dataset](https://www.bdd100k.com/)

---

<p align="center">
  <i>Computer Vision Group | University of Freiburg</i>
</p>
