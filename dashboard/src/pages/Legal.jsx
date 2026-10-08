import { ArrowLeft } from 'lucide-react'

const CONTACT = 'carbonomics.app@gmail.com'
const UPDATED = '8 October 2026'

function Page({ title, children }) {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-8">
        <a href="#home" className="flex items-center gap-2.5">
          <img src="./favicon.svg" alt="" className="h-9 w-9" />
          <span className="font-semibold text-slate-900 dark:text-white">Carbonomics-AI</span>
        </a>
        <a href="#home" className="muted inline-flex items-center gap-1.5 text-sm hover:underline"><ArrowLeft size={15} /> Home</a>
      </header>
      <main className="mx-auto max-w-3xl px-4 pb-16 pt-6 sm:px-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">{title}</h1>
        <p className="muted mt-2 text-sm">Last updated {UPDATED}</p>
        <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          This text was written by the project team for a final-year academic project. It describes what the site actually does today. It is not legal advice.
        </p>
        <div className="mt-8 space-y-8 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{children}</div>
        <nav className="muted mt-12 flex gap-4 border-t border-slate-200 pt-6 text-xs dark:border-slate-800">
          <a className="underline" href="#privacy">Privacy Policy</a>
          <a className="underline" href="#terms">Terms of Use</a>
          <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>
        </nav>
      </main>
    </div>
  )
}

const H = ({ children }) => <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">{children}</h2>
const Ul = ({ children }) => <ul className="list-disc space-y-1.5 pl-5">{children}</ul>

export function Privacy() {
  return (
    <Page title="Privacy Policy">
      <section>
        <H>Who we are</H>
        <p>Carbonomics-AI is built by Team Carbonomics, a final-year student team of the Department of AI &amp; DS, K. K. Wagh Institute of Engineering Education and Research (KKWIEER), Nashik. Contact: <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>. Questions about your data go to the same address.</p>
      </section>
      <section>
        <H>What the demo pages collect</H>
        <p>The home page and the demo pages (Overview to Data &amp; QA) need no login and show fixed project data. The site itself does not set advertising or analytics trackers. Your browser stores your colour theme (light or dark) locally. The host of the site (Vercel) may keep ordinary server logs such as IP address and page requests.</p>
      </section>
      <section>
        <H>What we store when you have an account</H>
        <p>Accounts are created by the team; there is no public sign-up. For each account we store:</p>
        <Ul>
          <li>your email address and a password (the password is stored only as a hash by our login provider, Supabase; we cannot read it);</li>
          <li>your name and role (for example Principal or Dean), set by the team;</li>
          <li>your history: for every analysis you run, the file name, an optional name you give the run, the date range, the aggregated electricity and diesel figures per period, the calculated emissions, forecast results and the emission factors used; and, only when you press "Save this scenario", the scenario settings and results.</li>
        </Ul>
        <p className="mt-2">Your login session is kept in your browser's local storage so you stay logged in. Logging out removes it.</p>
      </section>
      <section>
        <H>What we do not store</H>
        <p>The CSV file you upload is read in memory by the analysis server to calculate results and is not saved as a file. Only the results listed above are saved to your history. Please do not upload personal data (for example names or phone numbers); the tool only needs dates and consumption figures.</p>
      </section>
      <section>
        <H>Who can see your history</H>
        <p>Only you, through your own login. The database enforces this with row-level security, so one account cannot read another account's runs. The team members who administer the database can technically see stored data in the Supabase dashboard; they will not look at it except to keep the service working or at your request.</p>
      </section>
      <section>
        <H>Services we use</H>
        <Ul>
          <li>Supabase (login and database). Your account and history are stored on Supabase's cloud servers, not on college computers.</li>
          <li>Render (runs the analysis server) and Vercel (hosts the website).</li>
        </Ul>
        <p className="mt-2">These providers process data on our behalf to run the service. We do not sell your data or share it for advertising.</p>
      </section>
      <section>
        <H>Keeping and deleting data</H>
        <p>You can delete any saved run yourself on the History page. Your history is kept until you delete it or your account is closed. When an account is closed, its profile and history are deleted with it. Copies held in the provider's routine backups are removed on the provider's own schedule. To ask for your account or data to be deleted or corrected, write to <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.</p>
      </section>
      <section>
        <H>Security</H>
        <p>Connections use HTTPS. The server checks your login on every request except the health check. We do not claim the service is free of all risk; it is a student project run on free hosting plans.</p>
      </section>
      <section>
        <H>Requests for a demo</H>
        <p>"Request Demo" opens your email program with a pre-written message to us. We keep the emails we receive only to arrange the demo.</p>
      </section>
      <section>
        <H>Changes</H>
        <p>If this policy changes, the date at the top is updated. This project is run in India and Indian law applies to it. For any complaint about your data, write to <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.</p>
      </section>
    </Page>
  )
}

export function Terms() {
  return (
    <Page title="Terms of Use">
      <section>
        <H>About this service</H>
        <p>Carbonomics-AI is an academic project by Team Carbonomics, Department of AI &amp; DS, KKWIEER, Nashik. It helps estimate, forecast and compare carbon emissions from electricity and generator diesel. By using the site or logging in you agree to these terms.</p>
      </section>
      <section>
        <H>Estimates, not certified results</H>
        <Ul>
          <li>Results are estimates: activity (kWh, litres) multiplied by an emission factor. Each factor shows its source, version and unit on the site; some factors are marked unverified.</li>
          <li>Only the sources in your file (electricity and generator diesel) are calculated. Other sources are not included.</li>
          <li>Forecasts predict activity, not emissions, and a simple last-week guess is used when no model does better. They can be wrong.</li>
          <li>Scenarios use numbers you choose. They are not predictions of what a measure will achieve.</li>
          <li>Demo data labelled SYNTHETIC is generated and is not a measurement.</li>
          <li>The service is not an audit, a verification, a certification or professional advice. Do not use it alone for regulatory, financial or reporting decisions.</li>
        </Ul>
      </section>
      <section>
        <H>Accounts</H>
        <p>Accounts are created by the team for invited users. Keep your password private and tell us if you think someone else has used your account. We may suspend or close an account that is misused.</p>
      </section>
      <section>
        <H>Your data</H>
        <p>You must have the right to upload the data you provide. You keep ownership of your data; you allow us to process it to give you results and keep your history. See the <a className="underline" href="#privacy">Privacy Policy</a> for what is stored.</p>
      </section>
      <section>
        <H>Acceptable use</H>
        <Ul>
          <li>Do not try to break, overload or gain unauthorised access to the service or other users' data.</li>
          <li>Do not upload malicious files or personal data.</li>
          <li>Do not scrape, copy or resell the site.</li>
        </Ul>
      </section>
      <section>
        <H>Ownership</H>
        <p>© 2026 Team Carbonomics. All rights reserved. The content, design, data and code of this site may not be copied, reproduced or reused without written permission. Third-party emission-factor sources remain the property of their publishers and are cited on the site.</p>
      </section>
      <section>
        <H>Availability and liability</H>
        <p>The service runs on free hosting plans and may be slow, unavailable or change without notice; the first request after a quiet period can take about a minute. It is provided "as is", without warranties. To the extent allowed by law, the team and the college are not liable for losses arising from use of, or reliance on, the service.</p>
      </section>
      <section>
        <H>Changes and contact</H>
        <p>We may update these terms; the date at the top shows the latest version. These terms are governed by the laws of India, and the courts at Nashik, Maharashtra have jurisdiction. Questions: <a className="underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.</p>
      </section>
    </Page>
  )
}
