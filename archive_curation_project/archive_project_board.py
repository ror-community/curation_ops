import os
import sys
import csv
import github


GITHUB = {}
GITHUB['TOKEN'] = ''


def archive_project():
    curr_dir = os.getcwd() + '/'
    g = github.Github(GITHUB['TOKEN'])
    project_columns  = g.get_repo("ror-community/ror-updates").get_projects()[0].get_columns()
    for column in project_columns:
        column_name = column.name
        header = ['column_name', 'issue_id', 'issue_number', 'url', 'state', 'labels',
                  'created_at', 'updated_at', 'title', 'body', 'comments']
        issue_fields = ['id', 'number', 'html_url', 'state',
                        'created_at', 'updated_at', 'title', 'body']
        outfile = ''.join([curr_dir, column_name, '.csv'])
        with open(outfile, 'w') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(header)
        column_issues = [card.get_content()
                         for card in column.get_cards() if card.get_content() is not None]
        for issue in column_issues:
            issue_labels = '; '.join([label.name for label in issue.get_labels()])
            issue_comments = issue.get_comments()
            all_comments = []
            if issue_comments.totalCount != 0:
                for comment in issue_comments:
                    commenter = comment.user.login
                    comment_times = ' | '.join([comment.created_at.strftime("%m/%d/%Y, %H:%M:%S"), 
                        comment.updated_at.strftime("%m/%d/%Y, %H:%M:%S")])
                    comment_body = 'comment_text: ' + comment.body
                    comments_text = '\n'.join(
                        [commenter, comment_times, comment_body, '\n---\n'])
                    all_comments.append(comments_text)
            with open(outfile, 'a') as f_out:
                writer = csv.writer(f_out)
                issue_data = [getattr(issue, field) for field in issue_fields]
                issue_data.insert(0, column_name)
                issue_data.insert(5, issue_labels)
                issue_data.append(''.join(all_comments))
                writer.writerow(issue_data)


if __name__ == '__main__':
    archive_project()
