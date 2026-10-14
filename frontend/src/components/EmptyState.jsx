import { Inbox } from 'lucide-react'

export default function EmptyState({ title = 'Nothing here yet', description, action, icon: Icon = Inbox }) {
  return (
    <div className="empty-state">
      <Icon size={40} className="empty-state__icon" aria-hidden />
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && <div className="mt-16">{action}</div>}
    </div>
  )
}
