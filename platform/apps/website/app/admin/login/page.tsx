import { redirect } from 'next/navigation';
import {
  isAdmin,
  passwordMatches,
  setAdminCookie,
} from '@/lib/auth';

export const metadata = { title: 'Admin · Login' };
export const dynamic = 'force-dynamic';

async function attemptLogin(formData: FormData) {
  'use server';
  const password = String(formData.get('password') ?? '');
  if (!passwordMatches(password)) {
    redirect('/admin/login?error=1');
  }
  await setAdminCookie();
  redirect('/admin');
}

export default async function AdminLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  if (await isAdmin()) redirect('/admin');
  const sp = await searchParams;
  const showError = sp.error === '1';

  return (
    <article style={{ maxWidth: '24rem', paddingTop: 64 }}>
      <div className="ts-meta">Admin · login</div>
      <h1 className="hero-h1" style={{ fontSize: '40px', margin: '8px 0 24px' }}>
        Sign in.
      </h1>
      <form action={attemptLogin}>
        <input
          type="password"
          name="password"
          autoComplete="current-password"
          placeholder="Password"
          aria-label="Admin password"
          required
          autoFocus
          style={{
            display: 'block',
            width: '100%',
            padding: '10px 12px',
            border: '1px solid var(--ts-rule)',
            background: 'var(--ts-paper)',
            fontFamily: 'inherit',
            fontSize: 16,
            marginBottom: 12,
          }}
        />
        <button type="submit" className="ts-btn ts-btn--primary">
          Sign in
        </button>
        {showError && (
          <p style={{ marginTop: 16, color: 'var(--ts-accent, #c8392b)' }}>
            Wrong password.
          </p>
        )}
      </form>
      <p style={{ marginTop: 24, fontSize: 12, color: 'var(--ts-mute)' }}>
        Set <code>ADMIN_PASSWORD</code> in your Vercel env vars to enable this
        gate.
      </p>
    </article>
  );
}
