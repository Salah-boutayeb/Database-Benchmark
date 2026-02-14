#!/usr/bin/env python3
"""
Generate benchmark comparison charts for the database report.
"""

import matplotlib.pyplot as plt
import numpy as np
import os

# Create output directory
os.makedirs('reports/charts', exist_ok=True)

# Color schemes
COLORS_DOC = ['#4CAF50', '#2196F3', '#FF9800']  # MongoDB, ArangoDB, RavenDB
COLORS_KV = ['#9C27B0', '#E91E63']  # DynamoDB, Riak

# ============================================================
# CHART 1: Document DB - Import Performance
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

databases = ['MongoDB', 'ArangoDB', 'RavenDB']
goodreads = [31.05, 144.93, 130.39]
amazon = [10.23, 29.32, 41.83]

x = np.arange(len(databases))
width = 0.35

bars1 = ax.bar(x - width/2, goodreads, width, label='Goodreads (2.36M)', color=COLORS_DOC, alpha=0.9)
bars2 = ax.bar(x + width/2, amazon, width, label='Amazon (568K)', color=COLORS_DOC, alpha=0.5)

ax.set_xlabel('Database', fontsize=12)
ax.set_ylabel('Time (seconds)', fontsize=12)
ax.set_title('Document Database Import Performance', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(databases)
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars1:
    height = bar.get_height()
    ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)
for bar in bars2:
    height = bar.get_height()
    ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)

plt.tight_layout()
plt.savefig('reports/charts/document_import.png', dpi=150, bbox_inches='tight')
print("✓ Generated: document_import.png")

# ============================================================
# CHART 2: Document DB - CRUD Performance
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

goodreads_crud = [2.56, 14.58, 75.97]
amazon_crud = [1.21, 3.41, 38.07]

bars1 = ax.bar(x - width/2, goodreads_crud, width, label='Goodreads (2.36M)', color=COLORS_DOC, alpha=0.9)
bars2 = ax.bar(x + width/2, amazon_crud, width, label='Amazon (568K)', color=COLORS_DOC, alpha=0.5)

ax.set_xlabel('Database', fontsize=12)
ax.set_ylabel('Time (seconds)', fontsize=12)
ax.set_title('Document Database CRUD Performance', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(databases)
ax.legend()
ax.grid(axis='y', alpha=0.3)

for bar in bars1:
    height = bar.get_height()
    ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)
for bar in bars2:
    height = bar.get_height()
    ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)

plt.tight_layout()
plt.savefig('reports/charts/document_crud.png', dpi=150, bbox_inches='tight')
print("✓ Generated: document_crud.png")

# ============================================================
# CHART 3: Key-Value DB - All Operations
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

kv_databases = ['DynamoDB', 'Riak KV']
insert = [113.70, 1187.49]
export = [633.22, 924.16]

x = np.arange(len(kv_databases))
width = 0.35

bars1 = ax.bar(x - width/2, insert, width, label='Insert (568K docs)', color=COLORS_KV, alpha=0.9)
bars2 = ax.bar(x + width/2, export, width, label='Export (full)', color=COLORS_KV, alpha=0.5)

ax.set_xlabel('Database', fontsize=12)
ax.set_ylabel('Time (seconds)', fontsize=12)
ax.set_title('Key-Value Database Performance (Amazon 568K)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(kv_databases)
ax.legend()
ax.grid(axis='y', alpha=0.3)

for bar in bars1 + bars2:
    height = bar.get_height()
    ax.annotate(f'{height:.0f}s', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('reports/charts/kv_performance.png', dpi=150, bbox_inches='tight')
print("✓ Generated: kv_performance.png")

# ============================================================
# CHART 4: Cross-Study Comparison (Amazon Insert)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

all_databases = ['MongoDB', 'ArangoDB', 'RavenDB', 'DynamoDB', 'Riak KV']
amazon_insert = [10.23, 29.32, 41.83, 113.70, 1187.49]
all_colors = COLORS_DOC + COLORS_KV

bars = ax.barh(all_databases, amazon_insert, color=all_colors, alpha=0.85)

ax.set_xlabel('Time (seconds)', fontsize=12)
ax.set_title('Insert Performance Comparison - Amazon 568K Docs', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# Add value labels
for bar, value in zip(bars, amazon_insert):
    ax.annotate(f'{value:.1f}s', xy=(value, bar.get_y() + bar.get_height()/2),
                xytext=(5, 0), textcoords='offset points', va='center', fontsize=10)

# Add speedup annotations
ax.annotate('🏆 Fastest', xy=(10.23, 0), xytext=(100, 0.2), fontsize=9, color='green')
ax.annotate('10.4x slower', xy=(113.70, 3), xytext=(150, 3), fontsize=9, color='gray')
ax.annotate('116x slower', xy=(1187.49, 4), xytext=(800, 4.2), fontsize=9, color='red')

plt.tight_layout()
plt.savefig('reports/charts/cross_comparison.png', dpi=150, bbox_inches='tight')
print("✓ Generated: cross_comparison.png")

# ============================================================
# CHART 5: Throughput Comparison
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

# Calculate throughput (MB/s)
throughput_doc = [367.1 / 10.23, 367.1 / 29.32, 367.1 / 41.83]  # Document DBs
throughput_kv = [367.1 / 113.70, 367.1 / 1187.49]  # KV DBs

all_throughput = throughput_doc + throughput_kv

bars = ax.bar(all_databases, all_throughput, color=all_colors, alpha=0.85)

ax.set_xlabel('Database', fontsize=12)
ax.set_ylabel('Throughput (MB/s)', fontsize=12)
ax.set_title('Insert Throughput Comparison', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

for bar, value in zip(bars, all_throughput):
    ax.annotate(f'{value:.1f}', xy=(bar.get_x() + bar.get_width()/2, value),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('reports/charts/throughput.png', dpi=150, bbox_inches='tight')
print("✓ Generated: throughput.png")

print("\n✅ All charts generated in reports/charts/")
