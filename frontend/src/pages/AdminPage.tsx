import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AdminOverview, AdminUser, Metrics } from '../adminTypes'
import { RequestsChart, TokensChart } from '../components/admin/Charts'
import Stat from '../components/admin/Stat'
import UsersTable from '../components/admin/UsersTable'
import Header from '../components/Header'
import { errMsg, fmtNum, fmtPct } from '../lib/format'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">{title}</h2>
      {children}
    </section>
  )
}

const ms = (n: number | null | undefined) => (typeof n === 'number' ? `${n.toLocaleString()} ms` : '–')

export default function AdminPage() {
  const [days, setDays] = useState(7)
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (d: number) => {
    setError(null)
    try {
      const [o, u, m] = await Promise.all([api.admin.overview(), api.admin.users(), api.admin.metrics(d)])
      setOverview(o)
      setUsers(u)
      setMetrics(m)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(days)
  }, [load, days])

  const deleteUser = async (u: AdminUser) => {
    if (
      !window.confirm(
        `Delete ${u.email}?\n\nThis permanently removes their account, ${u.chats} chat(s) and ${u.memories} memory note(s).`,
      )
    )
      return
    try {
      await api.admin.deleteUser(u.id)
      await load(days)
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const clearLockouts = async () => {
    try {
      await api.admin.clearLockouts()
      await load(days)
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const budgetPct = overview
    ? Math.min(100, (overview.budgets.global_used_today / overview.budgets.global_daily) * 100)
    : 0
  const th = 'px-3 py-2 text-left font-medium'

  return (
    <div className="flex h-dvh flex-col bg-gray-50">
      <Header />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl space-y-8 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h1 className="text-xl font-semibold">Admin dashboard</h1>
            <div className="flex items-center gap-2 text-sm">
              <label className="text-gray-500" htmlFor="days">
                Range
              </label>
              <select
                id="days"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="rounded bg-white shadow-soft px-2 py-1"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
              </select>
              <button onClick={() => void load(days)} className="rounded bg-white shadow-soft px-3 py-1 hover:bg-gray-50">
                Refresh
              </button>
              <Link to="/" className="text-blue-600 hover:underline">
                Chat
              </Link>
            </div>
          </div>

          {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {loading && <p className="text-sm text-gray-500">Loading…</p>}

          {overview && (
            <Section title="Today">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Users" value={`${overview.users.count}/${overview.users.max}`} hint="registered accounts" />
                <Stat label="Chats" value={overview.conversations} hint={`${overview.messages} messages in total`} />
                <Stat label="Requests today" value={overview.today.requests} hint={`${overview.today.guest_messages} guest messages`} />
                <Stat
                  label="Errors today"
                  value={overview.today.errors}
                  hint={`${overview.today.no_result} found nothing`}
                  tone={overview.today.errors > 0 ? 'bad' : undefined}
                />
                <Stat label="Memory notes" value={overview.memory_facts} />
                <Stat
                  label="Login lockouts"
                  value={overview.active_lockouts}
                  tone={overview.active_lockouts > 0 ? 'warn' : undefined}
                  hint={overview.active_lockouts > 0 ? 'active right now' : 'none active'}
                />
                <Stat
                  label="Page cache (since restart)"
                  value={fmtPct(overview.page_cache_since_restart.hit_rate)}
                  hint={`${overview.page_cache_since_restart.hits} hits / ${overview.page_cache_since_restart.misses} misses`}
                />
                <div className="rounded-xl bg-white shadow-soft p-3">
                  <div className="text-xs text-gray-500">Model providers</div>
                  <ul className="mt-1 space-y-0.5 text-sm">
                    {overview.providers.map((p) => (
                      <li key={p.name} className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${p.circuit_open ? 'bg-red-500' : 'bg-green-500'}`} />
                        {p.name}
                        {p.circuit_open && <span className="text-xs text-red-600">paused</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-3 rounded-xl bg-white shadow-soft p-3">
                <div className="flex items-center justify-between text-sm">
                  <span>Global token budget today</span>
                  <span className="text-gray-500">
                    {fmtNum(overview.budgets.global_used_today)} / {fmtNum(overview.budgets.global_daily)} (
                    {budgetPct.toFixed(0)}%)
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded bg-gray-100">
                  <div
                    className={`h-full ${budgetPct > 85 ? 'bg-red-500' : budgetPct > 60 ? 'bg-amber-500' : 'bg-blue-600'}`}
                    style={{ width: `${budgetPct}%` }}
                  />
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                  <span>Per-user limit: {fmtNum(overview.budgets.per_user_daily)} tokens/day</span>
                  {overview.active_lockouts > 0 && (
                    <button onClick={clearLockouts} className="text-blue-600 hover:underline">
                      Clear login lockouts
                    </button>
                  )}
                </div>
              </div>
            </Section>
          )}

          {metrics && (
            <>
              <Section title={`Last ${metrics.days} days`}>
                <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Stat label="Requests" value={metrics.totals.requests} hint={`${metrics.totals.active_users} active user(s)`} />
                  <Stat
                    label="Error rate"
                    value={fmtPct(metrics.totals.error_rate)}
                    tone={metrics.totals.error_rate > 0.1 ? 'bad' : undefined}
                    hint="real faults only"
                  />
                  <Stat label="Nothing found" value={fmtPct(metrics.totals.no_result_rate)} hint="not counted as errors" />
                  <Stat
                    label="Tokens"
                    value={fmtNum(metrics.totals.tokens_in + metrics.totals.tokens_out)}
                    hint={`${fmtNum(metrics.totals.tokens_in)} in · ${fmtNum(metrics.totals.tokens_out)} out`}
                  />
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <RequestsChart data={metrics.daily} />
                  <TokensChart data={metrics.daily} />
                </div>
              </Section>

              <Section title="Latency per step (successful runs)">
                <div className="overflow-x-auto rounded-xl bg-white shadow-soft">
                  <table className="w-full min-w-[520px] text-sm">
                    <thead className="bg-gray-50 text-xs text-gray-500">
                      <tr>
                        <th className={th}>Step</th>
                        <th className={th}>Runs</th>
                        <th className={th}>Average</th>
                        <th className={th}>p50</th>
                        <th className={th}>p95</th>
                        <th className={th}>Max</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.latency.length === 0 && (
                        <tr>
                          <td colSpan={6} className="p-4 text-center text-gray-500">
                            No data yet. Send a few chats first.
                          </td>
                        </tr>
                      )}
                      {metrics.latency.map((r) => (
                        <tr key={r.node} className="border-t">
                          <td className="px-3 py-2 font-medium">{r.node}</td>
                          <td className="px-3 py-2">{r.count}</td>
                          <td className="px-3 py-2">{ms(r.avg_ms)}</td>
                          <td className="px-3 py-2">{ms(r.p50_ms)}</td>
                          <td className="px-3 py-2">{ms(r.p95_ms)}</td>
                          <td className="px-3 py-2">{ms(r.max_ms)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  "request" is the whole chat turn. Steps that run in parallel overlap, so they don't add up to it.
                </p>
              </Section>

              <Section title="Breakdown">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  <div className="rounded-xl bg-white shadow-soft p-3 text-sm">
                    <h3 className="mb-2 font-medium">Normal vs Accurate</h3>
                    {metrics.modes.length === 0 ? (
                      <p className="text-gray-500">No data yet.</p>
                    ) : (
                      <table className="w-full text-xs">
                        <thead className="text-gray-500">
                          <tr>
                            <th className="text-left font-medium">Mode</th>
                            <th className="text-left font-medium">Requests</th>
                            <th className="text-left font-medium">Avg time</th>
                            <th className="text-left font-medium">Avg tokens</th>
                          </tr>
                        </thead>
                        <tbody>
                          {metrics.modes.map((m) => (
                            <tr key={m.mode} className="border-t">
                              <td className="py-1 capitalize">{m.mode}</td>
                              <td>{m.requests}</td>
                              <td>{ms(m.avg_latency_ms)}</td>
                              <td>{fmtNum(m.avg_tokens_per_request)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  <div className="rounded-xl bg-white shadow-soft p-3 text-sm">
                    <h3 className="mb-2 font-medium">Model usage</h3>
                    {Object.keys(metrics.providers.counts).length === 0 ? (
                      <p className="text-gray-500">No answers yet.</p>
                    ) : (
                      <ul className="space-y-0.5">
                        {Object.entries(metrics.providers.counts).map(([name, n]) => (
                          <li key={name} className="flex justify-between">
                            <span>{name}</span>
                            <span className="text-gray-500">{n} answers</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    <p className="mt-2 text-xs text-gray-500">
                      Fallback rate: {fmtPct(metrics.providers.fallback_rate)}
                      {metrics.providers.primary && <> (primary: {metrics.providers.primary})</>}
                    </p>
                  </div>

                  <div className="rounded-xl bg-white shadow-soft p-3 text-sm">
                    <h3 className="mb-2 font-medium">Audience, limits and cache</h3>
                    <ul className="space-y-0.5 text-xs">
                      <li className="flex justify-between">
                        <span>Guest requests</span>
                        <span>{metrics.audience.guest}</span>
                      </li>
                      <li className="flex justify-between">
                        <span>User requests</span>
                        <span>{metrics.audience.user}</span>
                      </li>
                      <li className="flex justify-between">
                        <span>Page cache hit rate</span>
                        <span>{fmtPct(metrics.cache.page_cache_hit_rate)}</span>
                      </li>
                      <li className="flex justify-between">
                        <span>Embedding cache hit rate</span>
                        <span>{fmtPct(metrics.cache.index_cache_hit_rate)}</span>
                      </li>
                      {Object.entries(metrics.rate_limits).map(([k, n]) => (
                        <li key={k} className="flex justify-between text-amber-700">
                          <span>Blocked: {k}</span>
                          <span>{n}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {metrics.tokens_by_node.length > 0 && (
                  <div className="mt-3 overflow-x-auto rounded-xl bg-white shadow-soft">
                    <table className="w-full min-w-[420px] text-sm">
                      <thead className="bg-gray-50 text-xs text-gray-500">
                        <tr>
                          <th className={th}>Step</th>
                          <th className={th}>Calls</th>
                          <th className={th}>Tokens in</th>
                          <th className={th}>Tokens out</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metrics.tokens_by_node.map((r) => (
                          <tr key={r.node} className="border-t">
                            <td className="px-3 py-2 font-medium">{r.node}</td>
                            <td className="px-3 py-2">{r.calls}</td>
                            <td className="px-3 py-2">{fmtNum(r.tokens_in)}</td>
                            <td className="px-3 py-2">{fmtNum(r.tokens_out)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Section>
            </>
          )}

          <Section title="Users">
            <UsersTable users={users} onDeleteUser={deleteUser} onChanged={() => void load(days)} />
          </Section>
        </div>
      </main>
    </div>
  )
}