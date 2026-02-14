
import matplotlib.pyplot as plt
import numpy as np
import os

# Data from benchmark results
datasets = ['Amazon (568K docs)', 'Goodreads (1.85M docs)']
dynamodb_insert_times = [118.47, 400.22]
riak_insert_times = [598.55, 1846.11]

dynamodb_throughput = [3.1, 4.47]
riak_throughput = [0.61, 0.97]

dynamodb_read_times = [1.3261, 2.3225]
riak_read_times = [1.6564, 1.6834]

dynamodb_cpu = [75.9, 66.5]
riak_cpu = [929.1, 973.5]

dynamodb_mem = [855.4, 2587.4]
riak_mem = [836.8, 2144.6]

# Setup
x = np.arange(len(datasets))
width = 0.35
output_dir = 'documentation_repports/images_kv'
os.makedirs(output_dir, exist_ok=True)

def create_bar_chart(title, ylabel, filename, data1, label1, data2, label2):
    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, data1, width, label=label1, color='#2f5597') # Blue for DynamoDB
    rects2 = ax.bar(x + width/2, data2, width, label=label2, color='#c00000') # Red for Riak

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend()

    ax.bar_label(rects1, padding=3, fmt='%.2f')
    ax.bar_label(rects2, padding=3, fmt='%.2f')

    fig.tight_layout()
    plt.savefig(f"{output_dir}/{filename}")
    plt.close()
    print(f"Generated {filename}")

# 1. Durée d'Insertion
create_bar_chart(
    'Durée d\'Insertion (Plus bas est mieux)', 
    'Secondes', 
    'kv_insert_duration.png',
    dynamodb_insert_times, 'DynamoDB',
    riak_insert_times, 'Riak'
)

# 2. Débit (Throughput)
create_bar_chart(
    'Débit d\'Insertion (Plus haut est mieux)', 
    'Mo/s', 
    'kv_insert_throughput.png',
    dynamodb_throughput, 'DynamoDB',
    riak_throughput, 'Riak'
)

# 3. Latence de Lecture
create_bar_chart(
    'Latence de Lecture pour 1000 Docs (Plus bas est mieux)', 
    'Secondes', 
    'kv_read_latency.png',
    dynamodb_read_times, 'DynamoDB',
    riak_read_times, 'Riak'
)

# 4. Consommation CPU
create_bar_chart(
    'Consommation CPU Moyenne (Plus bas est mieux)', 
    'CPU % (Somme des cœurs)', 
    'kv_cpu_usage.png',
    dynamodb_cpu, 'DynamoDB',
    riak_cpu, 'Riak'
)

# 5. Utilisation Mémoire
create_bar_chart(
    'Utilisation Mémoire Moyenne (Plus bas est mieux)', 
    'Mo', 
    'kv_memory_usage.png',
    dynamodb_mem, 'DynamoDB',
    riak_mem, 'Riak'
)
