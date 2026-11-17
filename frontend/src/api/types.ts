// Mirrors backend/app/schemas.py. Keep the two in sync.

export type UserRole = 'member' | 'admin'
export type Locale = 'en' | 'zh'
export type ActivityKind = 'regular' | 'meetup'
export type ActivityState = 'upcoming' | 'live' | 'awaiting_close' | 'closed'
export type SignupRole = 'reviewer' | 'observer' | 'participant'
export type InviteStatus = 'pending' | 'accepted' | 'declined' | 'withdrawn'
export type InviteSource = 'organizer' | 'cac'
export type GroupStatus = 'active' | 'archived'
export type GroupRole = 'leader' | 'member'
export type ContributionKind = 'sharing' | 'review' | 'meetup'

export interface Ref {
  id: number
  name: string
}

export interface Me {
  id: number
  name: string
  email: string | null
  role: UserRole
  locale: Locale
  phone: string | null
  bio: string | null
  created_at: string
}

export interface PublicConfig {
  app_name: string
  timezone: string
  time_grid: string[]
  slot_minutes: number
  reviewer_limit: number
  meetup_weekday: number
  meetup_window: [string, string]
  close_grace_minutes: number
  observer_rating_weight: number
  participation_lookback_days: number
  allow_registration: boolean
  allowed_email_domains: string[]
  mail_enabled: boolean
}

export interface Room {
  id: number
  name: string
  capacity: number | null
  notes: string
  is_active: boolean
}

export interface RoomSlot {
  id: number
  room: Room
  date: string
  start_time: string
  end_time: string
}

export interface RoomAvailability {
  room: Room
  available: boolean
  reason: 'no_slot' | 'booked' | 'shared' | null
  booked_by: Ref | null
  booked_activity_title: string | null
}

export interface SignupCounts {
  reviewers: number
  observers: number
  participants: number
  reviewer_limit: number | null
  reviewer_spots_left: number | null
}

export interface ViewerContext {
  signup_id: number | null
  signup_role: SignupRole | null
  can_manage: boolean
  pending_invite_id: number | null
}

export interface Activity {
  id: number
  title: string
  description: string
  kind: ActivityKind
  date: string
  start_time: string
  end_time: string
  state: ActivityState
  room: Room | null
  location: string
  video_url: string
  group: Ref | null
  organizer: Ref
  speakers: Ref[]
  counts: SignupCounts
  closed_at: string | null
  closed_on_time: boolean | null
  created_at: string
  viewer: ViewerContext
}

export interface Rating {
  id: number
  rater: Ref
  score: number
  weight: number
  comment: string
  updated_at: string
}

export interface Signup {
  id: number
  user: Ref
  role: SignupRole
  review_topic: string
  review_doc_url: string
  review_submitted_at: string | null
  created_at: string
  email: string | null
  phone: string | null
  average_score: number | null
  rating_count: number
  my_score: number | null
  ratings: Rating[] | null
}

export interface ActivityDetail extends Activity {
  signups: Signup[]
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ActivityInput {
  title: string
  description: string
  kind: ActivityKind
  date: string
  start_time: string
  end_time: string
  room_id: number | null
  location: string
  video_url: string
  group_id: number | null
  speaker_ids: number[]
  acknowledge_warnings?: boolean
}

export interface Issue {
  code: string
  message: string
  activity_id: number | null
  activity_title: string | null
}

export interface ScheduleCheck {
  errors: Issue[]
  warnings: Issue[]
}

export interface CloseResult {
  activity: Activity
  on_time: boolean
  reminders_sent: number
}

export interface ReviewToRate {
  signup_id: number
  reviewer: Ref
  review_doc_url: string
  review_topic: string
  activity: Ref
  activity_date: string
  weight: number
}

export interface MySignup {
  id: number
  role: SignupRole
  review_topic: string
  review_doc_url: string
  review_submitted_at: string | null
  average_score: number | null
  rating_count: number
  activity: Activity
}

export interface Invite {
  id: number
  activity: Ref
  activity_date: string
  activity_start_time: string
  inviter: Ref | null
  invitee: Ref
  source: InviteSource
  status: InviteStatus
  message: string
  created_at: string
  updated_at: string
}

export interface Group {
  id: number
  name: string
  goal: string
  time_boundary: string
  plan: string
  description: string
  status: GroupStatus
  created_at: string
  leader: Ref | null
  member_count: number
  is_member: boolean
}

export interface GroupMember {
  user: Ref
  role: GroupRole
  joined_at: string
}

export interface GroupDetail extends Group {
  members: GroupMember[]
  recent_activities: Activity[]
}

export interface GroupInput {
  name: string
  goal: string
  time_boundary: string
  plan: string
  description: string
  member_ids?: number[]
  status?: GroupStatus
}

export interface CountEntry {
  user: Ref
  count: number
}

export interface ReviewQualityEntry {
  user: Ref
  score: number
  rating_count: number
  review_count: number
}

export interface PunctualityEntry {
  user: Ref
  closed_count: number
  on_time_count: number
  on_time_rate: number
}

export interface Leaderboards {
  sharing: CountEntry[]
  participation: CountEntry[]
  review_quality: ReviewQualityEntry[]
  punctuality: PunctualityEntry[]
  since: string | null
}

export interface Overview {
  upcoming_count: number
  activities_this_month: number
  members: number
  groups: number
}

export type TaskKind =
  | 'inactive'
  | 'missing_email'
  | 'join_group'
  | 'pending_invite'
  | 'submit_review'
  | 'close_activity'
  | 'rate_reviews'

export interface Task {
  kind: TaskKind
  priority: number
  activity: Ref | null
  invite_id: number | null
  signup_id: number | null
  count: number | null
}

export interface Recommendation {
  activity: Activity
  suggested_role: SignupRole
  reasons: string[]
}

export interface PersonalMetrics {
  share_count: number
  participation_count: number
  review_score: number | null
  review_rating_count: number
  on_time_rate: number | null
  closed_count: number
  recent_outputs: number
  lookback_days: number
  is_inactive: boolean
  ranks: Record<'sharing' | 'participation' | 'review_quality' | 'punctuality', number | null>
}

export interface MyGroup {
  id: number
  name: string
  role: GroupRole
}

export interface MeDashboard {
  metrics: PersonalMetrics
  tasks: Task[]
  upcoming: MySignup[]
  organizing: Activity[]
  groups: MyGroup[]
  invites: Invite[]
  recommendations: Recommendation[]
}

export interface Contribution {
  id: number
  user: Ref
  kind: ContributionKind
  date: string
  note: string
  created_at: string
}

export interface HistoryEntry {
  kind: 'spoke' | 'organized' | 'signed_up' | 'contribution'
  date: string
  activity: Activity | null
  role: SignupRole | null
  contribution: Contribution | null
}

export interface PublicProfile {
  user: Ref
  bio: string | null
  joined_at: string
  groups: MyGroup[]
  metrics: PersonalMetrics
  history: HistoryEntry[]
}

export interface AdminUser {
  id: number
  name: string
  email: string | null
  role: UserRole
  is_active: boolean
  is_claimed: boolean
  participation_tracked: boolean
  created_at: string
  last_login_at: string | null
}

export interface MonthlyReport {
  month: string
  activity_count: number
  regular_count: number
  meetup_count: number
  signup_count: number
  contribution_count: number
  active_organizers: number
  active_participants: number
  closed_count: number
  awaiting_close_count: number
  on_time_close_rate: number | null
}

export interface GroupHealth {
  group: Ref
  leader: Ref | null
  member_count: number
  active_member_count: number
  recent_activity_count: number
  awaiting_close_count: number
  score: number
  status: 'healthy' | 'at_risk' | 'inactive'
}

export interface ReviewerWatchEntry {
  user: Ref
  score: number | null
  rating_count: number
  review_count: number
  missing_docs: number
  status: 'missing_docs' | 'low_score' | 'needs_feedback' | 'ok'
}

export interface AdminDashboard {
  monthly: MonthlyReport
  participation: { lookback_days: number; tracked_count: number; inactive: Ref[] }
  groups: GroupHealth[]
  reviewers: ReviewerWatchEntry[]
  conflicts: { date: string; activities: Activity[] }[]
}
