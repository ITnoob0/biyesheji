export const resolvePostLoginRedirect = (routeRedirect, storedRedirect) => {
  if (typeof storedRedirect === 'string' && storedRedirect.trim() && storedRedirect !== '/login') {
    return storedRedirect
  }

  if (typeof routeRedirect === 'string' && routeRedirect.trim() && routeRedirect !== '/login') {
    return routeRedirect
  }

  return '/dashboard'
}
