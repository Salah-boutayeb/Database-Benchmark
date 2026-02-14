
import matplotlib.pyplot as plt
import numpy as np
import os

# Data from results/all_metrics.json
datasets = ['Amazon (568K docs)', 'Goodreads (1.85M docs)']

# Insert Duration (seconds)
# Amazon: Mongo 10.23, Arango 29.32, Raven 41.83
# Goodreads: Mongo 31.05, Arango 144.93, Raven 130.39
mongo_insert_times = [10.23, 31.05]
arango_insert_times = [29.32, 144.93]
raven_insert_times = [41.83, 130.39]

# Insert Throughput (Docs/sec)
# Amazon (568,454 docs) / duration
mongo_throughput = [568454/10.23, 568454/31.05] # ~55k, ~18k (wait, 1.85M for GR)
# Goodreads (1,849,236 docs) / duration
mongo_throughput_gr = 1849236/31.05 # ~59k
# Recalculating arrays properly:
mongo_throughput = [568454/10.23, 1849236/31.05]
arango_throughput = [568454/29.32, 1849236/144.93]
raven_throughput = [568454/41.83, 1849236/130.39]

# CRUD Duration (seconds) - Read/Update/Delete Mix
# Amazon: Mongo 1.21, Arango 3.41, Raven 38.07
# Goodreads: Mongo 2.56, Arango 14.58, Raven 75.97
mongo_crud_times = [1.21, 2.56]
arango_crud_times = [3.41, 14.58]
raven_crud_times = [38.07, 75.97]

# Export Duration (seconds)
# Amazon: Mongo 5.15, Arango 9.83, Raven 24.95
# Goodreads: Mongo 29.17, Arango 37.87, Raven 89.08
mongo_export_times = [5.15, 29.17]
arango_export_times = [9.83, 37.87]
raven_export_times = [24.95, 89.08]

# Resources - Import CPU % (Average)
# Amazon: Mongo 37.49, Arango 62.89, Raven 54.48
# Goodreads: Mongo 64.22, Arango 59.53, Raven 61.18
mongo_cpu = [37.49, 64.22]
arango_cpu = [62.89, 59.53]
raven_cpu = [54.48, 61.18]

# Resources - Import RAM (MB Max) - Better to show Max for peak usage or Avg?
# Let's use AVG as in previous report, but for Goodreads Mongo was 1078 avg vs 2030 max.
# Let's stick to AVG to be consistent with Study 2 report (which used container_mem_avg_mb).
# Amazon: Mongo 2326, Arango 2450, Raven 2484
# Goodreads: Mongo 1078, Arango 430, Raven 2818
# (Note: Arango/Mongo RAM seems low on GR, possibly successful streaming or GC. Raven used reliable RAM).
mongo_mem = [2326.53, 1078.37] 
arango_mem = [2450.57, 429.57]
raven_mem = [2484.61, 2817.91]

# Setup
x = np.arange(len(datasets))
width = 0.25 # Slimmer bars for 3 groups
output_dir = 'documentation_repports/images_doc'
os.makedirs(output_dir, exist_ok=True)

def create_bar_chart(title, ylabel, filename, d1, l1, d2, l2, d3, l3):
    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - width, d1, width, label=l1, color='#13aa52') # Green (Mongo)
    # Arango: Use Orange #ff9800
    rects2 = ax.bar(x, d2, width, label=l2, color='#ff9800')
    rects3 = ax.bar(x + width, d3, width, label=l3, color='#4527a0') # Purple (Raven)

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend()

    ax.bar_label(rects1, padding=3, fmt='%.1f')
    ax.bar_label(rects2, padding=3, fmt='%.1f')
    ax.bar_label(rects3, padding=3, fmt='%.1f')

    fig.tight_layout()
    plt.savefig(f"{output_dir}/{filename}")
    plt.close()
    print(f"Generated {filename}")

# 1. Durée d'Insertion
create_bar_chart(
    'Durée d\'Insertion (Plus bas est mieux)', 
    'Secondes', 
    'doc_insert_duration.png',
    mongo_insert_times, 'MongoDB',
    arango_insert_times, 'ArangoDB',
    raven_insert_times, 'RavenDB'
)

# 2. Débit (Throughput)
# Calculate throughput lists
mongo_th_val = [round(v, 0) for v in mongo_throughput]
arango_th_val = [round(v, 0) for v in arango_throughput]
raven_th_val = [round(v, 0) for v in raven_throughput]

create_bar_chart(
    'Débit d\'Insertion (Plus haut est mieux)', 
    'Docs/s', 
    'doc_insert_throughput.png',
    mongo_th_val, 'MongoDB',
    arango_th_val, 'ArangoDB',
    raven_th_val, 'RavenDB'
)

# 3. Durée CRUD (Read/Update/Delete)
create_bar_chart(
    'Durée Opérations CRUD (Plus bas est mieux)', 
    'Secondes', 
    'doc_crud_duration.png',
    mongo_crud_times, 'MongoDB',
    arango_crud_times, 'ArangoDB',
    raven_crud_times, 'RavenDB'
)

# 4. Durée Export
create_bar_chart(
    'Durée Exportation (Plus bas est mieux)', 
    'Secondes', 
    'doc_export_duration.png',
    mongo_export_times, 'MongoDB',
    arango_export_times, 'ArangoDB',
    raven_export_times, 'RavenDB'
)

# 5. Consommation CPU (Import)
create_bar_chart(
    'Consommation CPU Moyenne (Import) (Plus bas est mieux)', 
    'CPU %', 
    'doc_cpu_usage.png',
    mongo_cpu, 'MongoDB',
    arango_cpu, 'ArangoDB',
    raven_cpu, 'RavenDB'
)

# 6. Utilisation Mémoire (Import)
create_bar_chart(
    'Utilisation Mémoire Moyenne (Import) (Plus bas est mieux)', 
    'Mo', 
    'doc_memory_usage.png',
    mongo_mem, 'MongoDB',
    arango_mem, 'ArangoDB',
    raven_mem, 'RavenDB'
)
