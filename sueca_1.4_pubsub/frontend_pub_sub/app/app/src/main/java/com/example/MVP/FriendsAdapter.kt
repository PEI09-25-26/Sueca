package com.example.MVP

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.TextView
import com.example.MVP.models.UserData

class FriendsAdapter(
    context: Context,
    private val friends: List<UserData>
) : ArrayAdapter<UserData>(context, R.layout.friend_list_item, friends) {

    override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
        val view = convertView ?: LayoutInflater.from(context)
            .inflate(R.layout.friend_list_item, parent, false)

        val friend = friends[position]
        val statusDot = view.findViewById<View>(R.id.friend_status_dot)
        val usernameTextView = view.findViewById<TextView>(R.id.friend_username)

        usernameTextView.text = friend.username

        if (friend.status == "online") {
            statusDot.setBackgroundResource(R.drawable.status_indicator_online)
        } else {
            statusDot.setBackgroundResource(R.drawable.status_indicator_offline)
        }

        return view
    }
}
