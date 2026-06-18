import React from 'react';
import { StyleSheet, View } from 'react-native';
import { palette } from '../constants/theme';

type Props = {
  size?: number;
};

type Node = { x: number; y: number; gold?: boolean; large?: boolean };
type Link = { x1: number; y1: number; x2: number; y2: number };

const NODES: Node[] = [
  { x: 0.5, y: 0.08, gold: true },
  { x: 0.28, y: 0.2 },
  { x: 0.72, y: 0.2 },
  { x: 0.5, y: 0.34, gold: true },
  { x: 0.28, y: 0.46 },
  { x: 0.72, y: 0.46 },
  { x: 0.5, y: 0.6, large: true },
  { x: 0.28, y: 0.74 },
  { x: 0.72, y: 0.74 },
  { x: 0.5, y: 0.88, gold: true },
];

const LINKS: Link[] = [
  { x1: 0.5, y1: 0.08, x2: 0.28, y2: 0.2 },
  { x1: 0.5, y1: 0.08, x2: 0.72, y2: 0.2 },
  { x1: 0.28, y1: 0.2, x2: 0.5, y2: 0.34 },
  { x1: 0.72, y1: 0.2, x2: 0.5, y2: 0.34 },
  { x1: 0.28, y1: 0.2, x2: 0.28, y2: 0.46 },
  { x1: 0.72, y1: 0.2, x2: 0.72, y2: 0.46 },
  { x1: 0.5, y1: 0.34, x2: 0.28, y2: 0.46 },
  { x1: 0.5, y1: 0.34, x2: 0.72, y2: 0.46 },
  { x1: 0.5, y1: 0.34, x2: 0.5, y2: 0.6 },
  { x1: 0.28, y1: 0.46, x2: 0.5, y2: 0.6 },
  { x1: 0.72, y1: 0.46, x2: 0.5, y2: 0.6 },
  { x1: 0.28, y1: 0.46, x2: 0.28, y2: 0.74 },
  { x1: 0.72, y1: 0.46, x2: 0.72, y2: 0.74 },
  { x1: 0.5, y1: 0.6, x2: 0.28, y2: 0.74 },
  { x1: 0.5, y1: 0.6, x2: 0.72, y2: 0.74 },
  { x1: 0.28, y1: 0.74, x2: 0.5, y2: 0.88 },
  { x1: 0.72, y1: 0.74, x2: 0.5, y2: 0.88 },
  { x1: 0.5, y1: 0.6, x2: 0.5, y2: 0.88 },
];

export function BrandMark({ size = 72 }: Props) {
  const outerSize = size;
  const frameSize = Math.round(size * 0.74);
  const lineThickness = Math.max(1, Math.round(size * 0.016));

  return (
    <View style={[styles.outer, { width: outerSize, height: outerSize, borderRadius: outerSize / 2 }]}> 
      <View style={[styles.frame, { width: frameSize, height: frameSize, borderRadius: Math.round(size * 0.22) }]}>
        {LINKS.map((link, index) => {
          const dx = link.x2 - link.x1;
          const dy = link.y2 - link.y1;
          const length = Math.sqrt(dx * dx + dy * dy) * frameSize;
          const angle = Math.atan2(dy, dx);
          return (
            <View
              key={`link-${index}`}
              style={[
                styles.link,
                {
                  left: link.x1 * frameSize,
                  top: link.y1 * frameSize,
                  width: length,
                  height: lineThickness,
                  transform: [{ translateY: -lineThickness / 2 }, { rotate: `${angle}rad` }],
                },
              ]}
            />
          );
        })}
        {NODES.map((node, index) => {
          const diameter = node.large ? Math.max(9, Math.round(size * 0.12)) : Math.max(8, Math.round(size * 0.1));
          return (
            <View
              key={`node-${index}`}
              style={[
                styles.node,
                node.gold ? styles.nodeGold : styles.nodeLight,
                {
                  width: diameter,
                  height: diameter,
                  borderRadius: diameter / 2,
                  left: node.x * frameSize - diameter / 2,
                  top: node.y * frameSize - diameter / 2,
                },
              ]}
            />
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.borderStrong,
    shadowColor: '#000000',
    shadowOpacity: 0,
    shadowRadius: 0,
    shadowOffset: { width: 0, height: 0 },
    elevation: 0,
  },
  frame: {
    backgroundColor: palette.surfaceStrong,
    borderWidth: 1,
    borderColor: palette.border,
    position: 'relative',
    overflow: 'hidden',
  },
  link: {
    position: 'absolute',
    backgroundColor: palette.ink,
    transformOrigin: 'left center',
  },
  node: {
    position: 'absolute',
    borderWidth: 1,
  },
  nodeGold: {
    backgroundColor: palette.ink,
    borderColor: palette.ink,
  },
  nodeLight: {
    backgroundColor: palette.surface,
    borderColor: palette.borderStrong,
  },
});
