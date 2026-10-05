// Reusable project list shell. The caller decides how each row renders (a
// link to the project, a join button, etc.) via `renderItem`, so the same
// list works for both "my projects" and "other projects".
export default function ProjectList({ projects, emptyText, renderItem }) {
  if (projects.length === 0) return <p>{emptyText}</p>

  return (
    <ul className="project-list">
      {projects.map((project) => (
        <li key={project.id}>{renderItem(project)}</li>
      ))}
    </ul>
  )
}
