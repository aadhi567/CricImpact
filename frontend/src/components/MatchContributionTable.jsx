import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ExternalLink, CheckCircle2, XCircle } from 'lucide-react';

export default function MatchContributionTable({ matches = [], playerId }) {
  const navigate = useNavigate();
  const [filterMode, setFilterMode] = useState('batting');

  const filteredMatches = matches.filter((m) => {
    if (filterMode === 'batting') {
      return !m.is_dnb;
    }
    return true;
  });

  return (
    <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] shadow-xs overflow-hidden max-w-full min-w-0">
      {/* Table Header and Toggle */}
      <div className="p-3 sm:p-4 border-b border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div>
          <h3 className="font-heading text-[15px] sm:text-[16px] font-bold text-[#F2F2F2]">
            Match-by-match contextual innings
          </h3>
          <p className="text-[11.5px] font-normal text-[#858585] mt-0.5">
            Click any match row or action to inspect the situation and score breakdown.
          </p>
        </div>

        {/* View Toggle */}
        <div className="inline-flex rounded-lg bg-[#101010] p-0.5 border border-[#2D2D2D] self-start sm:self-auto">
          <button
            onClick={() => setFilterMode('batting')}
            className={`px-2.5 py-1 rounded-md text-[11.5px] font-semibold transition-colors cursor-pointer ${
              filterMode === 'batting'
                ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                : 'text-[#858585] hover:text-[#F2F2F2]'
            }`}
          >
            Batting innings only ({matches.filter((m) => !m.is_dnb).length})
          </button>
          <button
            onClick={() => setFilterMode('all')}
            className={`px-2.5 py-1 rounded-md text-[11.5px] font-semibold transition-colors cursor-pointer ${
              filterMode === 'all'
                ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                : 'text-[#858585] hover:text-[#F2F2F2]'
            }`}
          >
            All matches ({matches.length})
          </button>
        </div>
      </div>

      {/* Responsive Table Wrapper */}
      <div className="overflow-x-auto max-w-full min-w-0">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#2D2D2D] bg-[#161616] text-[#858585] text-[11px] sm:text-[11.5px] font-semibold uppercase tracking-wider">
              <th className="py-2.5 px-3">Match / Date</th>
              <th className="py-2.5 px-3">Opponent</th>
              <th className="py-2.5 px-2 text-center">Inn</th>
              <th className="py-2.5 px-2.5 text-center">Entry - Exit</th>
              <th className="py-2.5 px-2.5 text-right">Runs</th>
              <th className="py-2.5 px-2 text-right">Balls</th>
              <th className="py-2.5 px-2.5 text-right">SR</th>
              <th className="py-2.5 px-3 text-center">Contribution</th>
              <th className="py-2.5 px-2.5 text-right">Raw (C_raw)</th>
              <th className="py-2.5 px-2.5 text-center">Result</th>
              <th className="py-2.5 px-2.5 text-center">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[12.5px]">
            {filteredMatches.length === 0 ? (
              <tr>
                <td colSpan="11" className="py-6 text-center text-[#858585] text-xs">
                  No matching innings found.
                </td>
              </tr>
            ) : (
              filteredMatches.map((m) => {
                const isDnb = m.is_dnb;
                const score = m.contribution_score;
                const raw = m.raw_contribution;

                // Score styling
                let scoreBadge = 'bg-[#101010] text-[#858585] border-[#2D2D2D]';
                if (!isDnb && score !== null && score !== undefined) {
                  if (score >= 65) scoreBadge = 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30] font-bold';
                  else if (score >= 52) scoreBadge = 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30]/60 font-semibold';
                  else if (score >= 48) scoreBadge = 'bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/40 font-medium';
                  else scoreBadge = 'bg-[#271414] text-[#C25454] border border-[#4D2626] font-semibold';
                }

                return (
                  <tr
                    key={m.match_id}
                    onClick={() => navigate(`/match/${m.match_id}/player/${encodeURIComponent(playerId)}`)}
                    className={`cursor-pointer transition-colors hover:bg-[#1A1A1A] ${
                      isDnb ? 'bg-[#101010]/60 opacity-70 italic' : ''
                    }`}
                  >
                    {/* Match & Date */}
                    <td className="py-2 px-3 whitespace-nowrap">
                      <div className="font-semibold text-[#F2F2F2] text-[13px]">{m.date || `Match #${m.match_id}`}</div>
                      <div className="text-[11.5px] text-[#858585]">{m.venue || 'T20 Match'}</div>
                      {m.event_name && m.event_name !== 'Indian Premier League' && (
                        <div className="text-[10.5px] font-semibold text-[#D4AF57] tracking-wider uppercase mt-0.5">
                          {m.event_name}{m.stage ? ` • ${m.stage}` : ''}
                        </div>
                      )}
                    </td>

                    {/* Opponent */}
                    <td className="py-2 px-3 whitespace-nowrap font-medium text-[#B8B8B8] text-[12px] sm:text-[12.5px]">
                      vs {m.opponent || 'Opposition'}
                    </td>

                    {/* Innings */}
                    <td className="py-2 px-2 text-center whitespace-nowrap text-[#858585]">
                      {isDnb ? '-' : m.innings ? `${m.innings}` : '-'}
                    </td>

                    {/* Entry - Exit Overs */}
                    <td className="py-2 px-2.5 text-center whitespace-nowrap tabular-nums text-[12px] text-[#858585]">
                      {isDnb ? (
                        <span className="text-[#858585]">DNB</span>
                      ) : (
                        <span>
                          {m.entry_over !== null ? `ov ${m.entry_over}` : '-'} →{' '}
                          {m.exit_over !== null ? `ov ${m.exit_over}` : '-'}
                        </span>
                      )}
                    </td>

                    {/* Runs */}
                    <td className="py-2 px-2.5 text-right font-bold text-[#F2F2F2] whitespace-nowrap tabular-nums text-[13px]">
                      {isDnb ? (
                        <span className="text-[#858585] font-normal">N/A</span>
                      ) : (
                        <span>
                          {m.runs}
                          {m.dismissal_status && m.dismissal_status.toLowerCase() === 'not out' && '*'}
                        </span>
                      )}
                    </td>

                    {/* Balls */}
                    <td className="py-2 px-2 text-right whitespace-nowrap text-[#858585] tabular-nums">
                      {isDnb ? '—' : m.balls}
                    </td>

                    {/* SR */}
                    <td className="py-2 px-2.5 text-right whitespace-nowrap tabular-nums text-[#B8B8B8]">
                      {isDnb ? '—' : m.strike_rate !== null ? m.strike_rate.toFixed(1) : '—'}
                    </td>

                    {/* Contribution Score */}
                    <td className="py-2 px-3 text-center whitespace-nowrap">
                      {isDnb ? (
                        <span className="text-[11px] text-[#858585] font-semibold px-2 py-0.5 rounded bg-[#101010] border border-[#2D2D2D]">
                          —
                        </span>
                      ) : (
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[12px] border tabular-nums ${scoreBadge}`}>
                          {score !== null ? score.toFixed(1) : '—'}
                        </span>
                      )}
                    </td>

                    {/* Raw Contribution */}
                    <td className="py-2 px-2.5 text-right whitespace-nowrap tabular-nums text-[12px] font-mono font-medium">
                      {isDnb || raw === null ? (
                        <span className="text-[#858585] font-sans">—</span>
                      ) : (
                        <span className={raw >= 0 ? 'text-[#5A9E60]' : 'text-[#C25454]'}>
                          {raw > 0 ? `+${raw.toFixed(4)}` : raw.toFixed(4)}
                        </span>
                      )}
                    </td>

                    {/* Team Result */}
                    <td className="py-2 px-2.5 text-center whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                          m.team_result === 'Won'
                            ? 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30]'
                            : 'bg-[#271414] text-[#C25454] border border-[#4D2626]'
                        }`}
                      >
                        {m.team_result === 'Won' ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {m.team_result}
                      </span>
                    </td>

                    {/* Detail Link */}
                    <td className="py-2 px-2.5 text-center whitespace-nowrap">
                      <Link
                        to={`/match/${m.match_id}/player/${encodeURIComponent(playerId)}`}
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 text-[12px] text-[#D4AF57] hover:text-[#E1C878] font-semibold hover:underline p-0.5"
                        title="View Contextual Contribution Detail"
                      >
                        <span>View</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="p-2.5 bg-[#101010] border-t border-[#2D2D2D] text-[11px] text-[#858585] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1.5">
        <span>* Par Score = 50.0 (above-par &gt; 50.0, below-par &lt; 50.0).</span>
        <span>* DNB matches are strictly excluded from denominators and return N/A.</span>
      </div>
    </div>
  );
}
