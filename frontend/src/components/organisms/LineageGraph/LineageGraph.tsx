/**
 * LineageGraph Component (Organism)
 *
 * Interactive lineage graph visualization using React Flow
 */

import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box, Paper, Typography, Chip } from '@mui/material';
import type { LineageGraph as LineageGraphData } from '@types/api';
import { formatSourceType } from '@utils/formatting';

interface LineageGraphProps {
  data: LineageGraphData;
  onNodeClick?: (datasetId: string) => void;
}

// Color mapping for different source types
const sourceTypeColors: Record<string, string> = {
  postgres: '#336791',
  mysql: '#00758F',
  sqlserver: '#CC2927',
  dbt: '#FF694B',
  python: '#3776AB',
  iceberg: '#00B8D4',
  delta: '#E67E22',
  default: '#757575',
};

const getNodeColor = (sourceType: string): string => {
  return sourceTypeColors[sourceType] || sourceTypeColors.default;
};

const createDagreLayout = (nodes: Node[], edges: Edge[]) => {
  // Simple layered layout algorithm
  const layerMap = new Map<string, number>();
  const visited = new Set<string>();

  // Build adjacency list for edges
  const adjacency = new Map<string, string[]>();
  edges.forEach((edge) => {
    const targetId = edge.target;
    if (!adjacency.has(targetId)) {
      adjacency.set(targetId, []);
    }
    adjacency.get(targetId)!.push(edge.source);
  });

  // Assign layers using BFS
  const assignLayer = (nodeId: string, layer: number) => {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);

    const currentLayer = layerMap.get(nodeId) || 0;
    layerMap.set(nodeId, Math.max(currentLayer, layer));

    const parents = adjacency.get(nodeId) || [];
    parents.forEach((parentId) => assignLayer(parentId, layer - 1));
  };

  // Find leaf nodes (nodes with no outgoing edges)
  const leafNodes = nodes.filter((node) =>
    !edges.some((edge) => edge.source === node.id)
  );

  // Start from leaf nodes
  leafNodes.forEach((node) => assignLayer(node.id, 0));

  // Ensure all nodes have a layer
  nodes.forEach((node) => {
    if (!layerMap.has(node.id)) {
      layerMap.set(node.id, 0);
    }
  });

  // Count nodes per layer
  const layerCounts = new Map<number, number>();
  layerMap.forEach((layer) => {
    layerCounts.set(layer, (layerCounts.get(layer) || 0) + 1);
  });

  // Position nodes
  const layerPositions = new Map<number, number>();
  const layerWidth = 250;
  const layerHeight = 120;

  return nodes.map((node) => {
    const layer = layerMap.get(node.id) || 0;
    const positionInLayer = layerPositions.get(layer) || 0;
    layerPositions.set(layer, positionInLayer + 1);

    const nodesInLayer = layerCounts.get(layer) || 1;
    const yOffset = (positionInLayer - (nodesInLayer - 1) / 2) * layerHeight;

    return {
      ...node,
      position: {
        x: layer * layerWidth,
        y: yOffset,
      },
    };
  });
};

export const LineageGraph: React.FC<LineageGraphProps> = ({ data, onNodeClick }) => {
  // Convert lineage data to React Flow format
  const initialNodes = useMemo<Node[]>(() => {
    return data.datasets.map((dataset) => {
      const color = getNodeColor(dataset.source_type);

      return {
        id: dataset.id,
        type: 'default',
        data: {
          label: (
            <Box sx={{ textAlign: 'center', p: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                {dataset.name}
              </Typography>
              {dataset.schema_name && (
                <Typography variant="caption" color="text.secondary">
                  {dataset.schema_name}
                </Typography>
              )}
              <Box sx={{ mt: 0.5 }}>
                <Chip
                  label={formatSourceType(dataset.source_type)}
                  size="small"
                  sx={{
                    backgroundColor: color,
                    color: 'white',
                    fontSize: '0.7rem',
                    height: 20,
                  }}
                />
              </Box>
            </Box>
          ),
        },
        position: { x: 0, y: 0 }, // Will be set by layout
        style: {
          background: 'white',
          border: `2px solid ${color}`,
          borderRadius: 8,
          padding: 4,
          minWidth: 180,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });
  }, [data.datasets]);

  const initialEdges = useMemo<Edge[]>(() => {
    return data.edges.map((edge, index) => {
      // Determine source and target based on whether it's column-level or table-level
      const sourceId = edge.source_column_id
        ? edge.source_column_id
        : edge.source_dataset_id;
      const targetId = edge.target_column_id
        ? edge.target_column_id
        : edge.target_dataset_id;

      // For table-level edges, find the actual dataset IDs
      const source = edge.source_dataset_id || sourceId;
      const target = edge.target_dataset_id || targetId;

      return {
        id: edge.id || `edge-${index}`,
        source: source!,
        target: target!,
        type: 'smoothstep',
        animated: true,
        label: edge.expression || '',
        style: {
          stroke: '#64748b',
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#64748b',
        },
      };
    });
  }, [data.edges]);

  // Apply layout
  const layoutedNodes = useMemo(
    () => createDagreLayout(initialNodes, initialEdges),
    [initialNodes, initialEdges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  if (data.datasets.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No lineage data available for this dataset.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ width: '100%', height: 600 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        attributionPosition="bottom-right"
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        <MiniMap
          nodeColor={(node) => {
            const dataset = data.datasets.find((d) => d.id === node.id);
            return dataset ? getNodeColor(dataset.source_type) : '#ccc';
          }}
          nodeBorderRadius={8}
          style={{
            backgroundColor: '#f8fafc',
          }}
        />
      </ReactFlow>
    </Box>
  );
};

export default LineageGraph;
