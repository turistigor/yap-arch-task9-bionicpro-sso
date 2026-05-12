import React from 'react';
import { UserInfo } from './Auth';

interface UserBadgeProps {
  user: UserInfo;
}

export const UserBadge: React.FC<UserBadgeProps> = ({ user }) => (
  <div className="mb-6 p-3 bg-gray-50 rounded border border-gray-200 text-sm flex flex-col gap-1">
    <div className="flex justify-between">
      Logged in as: {user.preferred_username}
    </div>
    <div className="flex justify-between border-t border-gray-100 pt-1 mt-1">
      Email: {user.email}
    </div>
  </div>
);
