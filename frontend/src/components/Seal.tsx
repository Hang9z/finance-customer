import React from 'react';

interface SealProps {
  text: string;
  tone?: 'seal' | 'ink';
  className?: string;
}

export const Seal: React.FC<SealProps> = ({
  text,
  tone = 'seal',
  className = '',
}) => {
  const color = tone === 'seal' ? '#B5432F' : '#5B616B';

  return (
    <div
      className={`pointer-events-none select-none animate-seal-stamp ${className}`}
      aria-label={`电子印章：${text}`}
    >
      <svg
        width="68"
        height="68"
        viewBox="0 0 68 68"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="34"
          cy="34"
          r="31"
          stroke={color}
          strokeWidth="1.6"
          strokeDasharray="2 1"
        />
        <circle
          cx="34"
          cy="34"
          r="26"
          stroke={color}
          strokeWidth="1"
        />
        <text
          x="34"
          y="22"
          textAnchor="middle"
          fill={color}
          fontSize="6.5"
          letterSpacing="1.2"
          fontFamily='"Noto Serif SC", "Source Han Serif SC", serif'
          fontWeight="600"
        >
          中州银行
        </text>
        <text
          x="34"
          y="39"
          textAnchor="middle"
          fill={color}
          fontSize="11.5"
          letterSpacing="1"
          fontFamily='"Noto Serif SC", "Source Han Serif SC", serif'
          fontWeight="700"
        >
          {text}
        </text>
        <text
          x="34"
          y="50"
          textAnchor="middle"
          fill={color}
          fontSize="6"
          letterSpacing="1"
          fontFamily='"JetBrains Mono", monospace'
        >
          SEAL
        </text>
      </svg>
    </div>
  );
};
