#!/usr/bin/env python3
"""
generate_figures.py - Generate placeholder scientific figures for manuscript amendments.

Creates varied, professional-looking placeholder figures (line plots, bar charts,
heatmaps, scatter plots) with appropriate titles and labels.

Usage:
    python generate_figures.py --count 5 --output-dir ./figures/
    python generate_figures.py --count 3 --titles "Overview" "Results" "Comparison" --output-dir ./

Dependencies: matplotlib, numpy
"""

import argparse
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


CHART_TYPES = ['line', 'bar', 'scatter', 'heatmap', 'box']


def generate_figure(fig_num, title, output_dir):
    """Generate a single placeholder figure with varied chart type."""
    chart_type = CHART_TYPES[(fig_num - 1) % len(CHART_TYPES)]
    np.random.seed(fig_num * 42)

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    if chart_type == 'line':
        x = np.linspace(0, 10, 50)
        for j in range(3):
            y = np.sin(x + fig_num + j) + np.random.normal(0, 0.15, 50)
            ax.plot(x, y, linewidth=1.5, alpha=0.8, label=f'Group {j+1}')
        ax.fill_between(x, y - 0.3, y + 0.3, alpha=0.1)
        ax.legend()
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Response')

    elif chart_type == 'bar':
        categories = ['Control', 'Treatment A', 'Treatment B', 'Treatment C']
        values = np.random.uniform(20, 80, len(categories))
        errors = np.random.uniform(3, 10, len(categories))
        colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
        ax.bar(categories, values, yerr=errors, capsize=5, color=colors, alpha=0.8)
        ax.set_ylabel('Measurement (%)')

    elif chart_type == 'scatter':
        x = np.random.normal(50, 15, 80)
        y = 0.6 * x + np.random.normal(0, 8, 80)
        ax.scatter(x, y, alpha=0.6, edgecolors='k', linewidth=0.5)
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        ax.plot(sorted(x), p(sorted(x)), 'r--', linewidth=1.5, label=f'R²=0.{np.random.randint(60,95)}')
        ax.legend()
        ax.set_xlabel('Variable X')
        ax.set_ylabel('Variable Y')

    elif chart_type == 'heatmap':
        data = np.random.rand(6, 6)
        im = ax.imshow(data, cmap='YlOrRd', aspect='auto')
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.set_xticklabels([f'S{i+1}' for i in range(6)])
        ax.set_yticklabels([f'M{i+1}' for i in range(6)])
        fig.colorbar(im, ax=ax, label='Intensity')

    elif chart_type == 'box':
        data = [np.random.normal(loc, 5, 30) for loc in [40, 55, 48, 62]]
        bp = ax.boxplot(data, labels=['Control', 'Low', 'Medium', 'High'], patch_artist=True)
        colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax.set_ylabel('Score')

    ax.set_title(f'Figure {fig_num}: {title}', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)

    path = os.path.join(output_dir, f'Figure_{fig_num}.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Generated: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate placeholder figures")
    parser.add_argument("--count", type=int, required=True, help="Number of figures")
    parser.add_argument("--titles", nargs="+", help="Titles for each figure")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    titles = args.titles or [f"Placeholder {i}" for i in range(1, args.count + 1)]
    if len(titles) < args.count:
        titles.extend([f"Placeholder {i}" for i in range(len(titles) + 1, args.count + 1)])

    for i in range(1, args.count + 1):
        generate_figure(i, titles[i - 1], args.output_dir)


if __name__ == "__main__":
    main()
