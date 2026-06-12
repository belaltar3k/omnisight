import numpy as np
import torch


class Graph:
    def __init__(self):
        self.num_node = 17

        # COCO-style skeleton edges
        self.edges = [
            (15, 13), (13, 11),
            (16, 14), (14, 12),
            (11, 12),
            (5, 11), (6, 12),
            (5, 6),
            (5, 7), (7, 9),
            (6, 8), (8, 10),
            (1, 2),
            (0, 1), (0, 2),
            (1, 3), (2, 4),
            (3, 5), (4, 6),
        ]

        self.center = [11, 12]
        self.A = self.get_adj()

    def get_adj(self):
        # Base adjacency matrix
        A = np.zeros((self.num_node, self.num_node), dtype=np.float32)

        for i, j in self.edges:
            A[i, j] = 1.0
            A[j, i] = 1.0

        # -------------------------------------------------
        # Compute hop distance from torso center nodes
        # -------------------------------------------------
        dist = np.full(self.num_node, -1, dtype=np.int32)
        queue = list(self.center)

        for c in self.center:
            dist[c] = 0

        while queue:
            node = queue.pop(0)
            for nb in range(self.num_node):
                if A[node, nb] > 0 and dist[nb] < 0:
                    dist[nb] = dist[node] + 1
                    queue.append(nb)

        # Any disconnected node becomes 0
        dist[dist < 0] = 0

        # -------------------------------------------------
        # Partitioned adjacency matrices
        # 0 = self connections
        # 1 = centripetal
        # 2 = centrifugal
        # -------------------------------------------------
        A_part = np.zeros((3, self.num_node, self.num_node), dtype=np.float32)

        # Self-links
        for i in range(self.num_node):
            A_part[0, i, i] = 1.0

        # Directed partitions
        for i, j in self.edges:
            if dist[i] < dist[j]:
                # i closer to center than j
                A_part[1, i, j] = 1.0
                A_part[2, j, i] = 1.0
            elif dist[i] > dist[j]:
                # j closer to center than i
                A_part[1, j, i] = 1.0
                A_part[2, i, j] = 1.0
            else:
                # Same distance from center
                A_part[1, i, j] = 1.0
                A_part[1, j, i] = 1.0

        # -------------------------------------------------
        # Symmetric normalization
        # Avoid divide-by-zero warning cleanly
        # -------------------------------------------------
        for k in range(3):
            row_sums = A_part[k].sum(axis=1)
            d = np.zeros_like(row_sums, dtype=np.float32)
            mask = row_sums > 0
            d[mask] = np.power(row_sums[mask], -0.5)
            D = np.diag(d)
            A_part[k] = D @ A_part[k] @ D

        return torch.tensor(A_part, dtype=torch.float32)


SkeletonGraph = Graph
