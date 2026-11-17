import { expect, test, type Page } from '@playwright/test'

const PASSWORD = 'password123'

async function signIn(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL('/')
  // Several demo members prefer Chinese; these tests assert on English copy.
  if ((await page.getAttribute('html', 'lang')) !== 'en') {
    await page.request.patch('/api/auth/me', { data: { locale: 'en' }, headers: { 'X-Requested-With': 'e2e' } })
    await page.reload()
  }
}

async function openActivity(page: Page, title: string) {
  const res = await page.request.get(`/api/activities?q=${encodeURIComponent(title)}`)
  const { items } = await res.json()
  await page.goto(`/activities/${items[0].id}`)
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
}

test('guests can browse sessions and switch language', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Learn by sharing' })).toBeVisible()
  await expect(page.getByText('Ownership in Rust, Visually')).toBeVisible()
  await page.getByRole('tab', { name: 'Past' }).click()
  await expect(page.getByText('Raft: Understandable Consensus')).toBeVisible()
  await page.getByTitle('Language').click()
  await expect(page.getByRole('heading', { name: '在分享中学习' })).toBeVisible()
})

test('a new member registers and schedules a session, confirming a clash', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel('Your name').fill('Test Organiser')
  await page.getByLabel('Email').fill('organiser@example.edu')
  await page.getByLabel('Password').fill('a long enough password')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: 'Hi Test Organiser' })).toBeVisible()

  // Put it on top of an existing session to trigger the overlap warning.
  const { items } = await (await page.request.get('/api/activities?q=Rust')).json()
  const rust = items[0]
  await page.goto('/activities/new')
  await page.getByLabel('Title').fill('Property-based testing in practice')
  await page.getByLabel('Date').fill(rust.date)
  await page.getByLabel('Starts').selectOption(rust.start_time)
  await page.getByLabel('Ends').selectOption(rust.end_time)
  await expect(page.getByText('Overlaps with “Ownership in Rust, Visually”')).toBeVisible()
  await page.getByRole('button', { name: 'Create session' }).click()
  await expect(page.getByRole('dialog', { name: 'Heads up before you save' })).toBeVisible()
  await page.getByRole('button', { name: 'Save anyway' }).click()

  await expect(page.getByRole('heading', { level: 1, name: 'Property-based testing in practice' })).toBeVisible()
  await expect(page.getByText('You’re speaking at this session.')).toBeVisible()
})

test('reviewer spots: sign up with a focus, then cancel', async ({ page }) => {
  await signIn(page, 'he.jing@example.edu')
  await openActivity(page, 'Prototyping in Figma in 60 Minutes')
  await page.getByLabel('What will you focus on?').fill('Auto-layout and component variants')
  await page.getByRole('button', { name: 'Sign up', exact: true }).click()
  await expect(page.getByText('You’re signed up as Reviewer')).toBeVisible()
  await expect(page.getByText('Auto-layout and component variants').first()).toBeVisible()
  await expect(page.getByText('1 / 3 reviewer spots')).toBeVisible()

  await page.getByRole('button', { name: 'Cancel my signup' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel my signup' }).click()
  await expect(page.getByText('Signup cancelled')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sign up', exact: true })).toBeVisible()
})

test('full review cycle: close, submit review, weighted rating', async ({ browser }) => {
  // Liu organises "eBPF for Observability", which ended two days ago.
  const liu = await (await browser.newContext()).newPage()
  await signIn(liu, 'liu.yang@example.edu')
  await openActivity(liu, 'eBPF for Observability')
  await liu.getByRole('button', { name: 'Close session' }).click()
  await liu.getByRole('dialog').getByRole('button', { name: 'Close session' }).click()
  await expect(liu.getByText(/Session closed\. 1 reviewer was reminded\./)).toBeVisible()
  await expect(liu.getByText('Closed', { exact: true })).toBeVisible()

  // Chen reviewed it and now submits the write-up.
  const chen = await (await browser.newContext()).newPage()
  await signIn(chen, 'chen.hao@example.edu')
  await openActivity(chen, 'eBPF for Observability')
  await chen.getByLabel('Link to your review document').fill('https://www.yuque.com/cac/reviews/ebpf-chen')
  await chen.getByRole('button', { name: 'Submit your review' }).click()
  await expect(chen.getByText('Review submitted — thank you!')).toBeVisible()

  // Tom observed, so his rating counts ten times.
  const tom = await (await browser.newContext()).newPage()
  await signIn(tom, 'tom.becker@example.edu')
  await tom.goto('/reviews')
  const review = tom.getByRole('listitem').filter({ hasText: 'Chen Hao' }).filter({ hasText: 'eBPF for Observability' })
  await expect(review.getByText('Counts ×10')).toBeVisible()
  await review.getByRole('button', { name: 'Rate' }).click()
  await tom.getByRole('radio', { name: '9' }).click()
  await tom.getByRole('dialog').getByRole('button', { name: 'Rate' }).click()
  await expect(tom.getByText('Thanks — rating saved')).toBeVisible()

  await openActivity(chen, 'eBPF for Observability')
  await expect(chen.getByText('Avg 9.0')).toBeVisible()
})

test('an invited member accepts by signing up', async ({ page }) => {
  await signIn(page, 'lin.yue@example.edu')
  await page.goto('/me')
  await expect(page.getByText('Respond to the review invitation for “Ownership in Rust, Visually”.')).toBeVisible()
  await openActivity(page, 'Ownership in Rust, Visually')
  await expect(page.getByText('Zhou Xin invited you to review this session.')).toBeVisible()
  await page.getByRole('button', { name: 'Accept & sign up' }).click()
  await page.getByLabel('What will you focus on?').fill('Borrow checker error messages')
  await page.getByRole('button', { name: 'Sign up', exact: true }).click()
  await expect(page.getByText('You’re signed up as Reviewer')).toBeVisible()
  const invites = await (await page.request.get('/api/me/invites')).json()
  expect(invites[0].status).toBe('accepted')
})

test('groups: create with a founding member, then someone joins', async ({ browser }) => {
  const xu = await (await browser.newContext()).newPage()
  await signIn(xu, 'xu.ran@example.edu')
  await xu.goto('/groups/new')
  await xu.getByLabel('Group name').fill('Compilers Club')
  await xu.getByLabel('Goal').fill('Write a toy compiler together')
  await xu.getByLabel('Timeframe').fill('Spring term')
  await xu.getByLabel('How we work').fill('Weekly pairing sessions')
  await xu.getByLabel('Founding members').fill('Guo')
  await xu.getByRole('option', { name: 'Guo Ming' }).click()
  await xu.getByRole('button', { name: 'Create', exact: true }).click()
  await expect(xu.getByRole('heading', { level: 1, name: 'Compilers Club' })).toBeVisible()
  await expect(xu.getByText('2 members')).toBeVisible()

  const sun = await (await browser.newContext()).newPage()
  await signIn(sun, 'sun.qi@example.edu')
  await sun.goto(xu.url())
  await sun.getByRole('button', { name: 'Join group' }).click()
  await expect(sun.getByText('Welcome to Compilers Club!')).toBeVisible()
  await expect(sun.getByText('3 members')).toBeVisible()
})

test('admins manage rooms and see the dashboard', async ({ page }) => {
  await signIn(page, 'admin@example.edu')
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Participation watch' })).toBeVisible()
  await page.getByRole('tab', { name: 'Rooms' }).click()
  await page.getByRole('button', { name: 'Add room' }).click()
  await page.getByRole('dialog').getByLabel('Name').fill('Library Seminar Room')
  await page.getByRole('dialog').getByRole('button', { name: 'Save' }).click()
  await expect(page.getByText('Library Seminar Room')).toBeVisible()
  await page.getByRole('tab', { name: 'Export' }).click()
  await expect(page.getByRole('link', { name: 'Sessions (CSV)' })).toHaveAttribute('href', /export\/activities\.csv/)
})

test('members cannot reach the admin area', async ({ page }) => {
  await signIn(page, 'guo.ming@example.edu')
  await page.goto('/admin')
  await expect(page).toHaveURL('/')
  const res = await page.request.get('/api/admin/dashboard')
  expect(res.status()).toBe(403)
})

test.describe('mobile', () => {
  test.use({ viewport: { width: 375, height: 740 }, isMobile: true, hasTouch: true })

  test('pages fit the screen without sideways scrolling', async ({ page }) => {
    await signIn(page, 'maya.patel@example.edu')
    for (const path of ['/', '/groups', '/leaderboards', '/me', '/activities/new']) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      const width = await page.evaluate(() => document.documentElement.scrollWidth)
      expect(width, path).toBeLessThanOrEqual(375)
    }
    await expect(page.getByRole('navigation').getByRole('link', { name: 'Explore' })).toBeVisible()
  })
})
