import os
import sys
import csv
import github


GITHUB = {}
GITHUB['TOKEN'] = ''



def curation_team_report():
    curr_dir = os.getcwd() + '/'
    g = github.Github(GITHUB['TOKEN'])
    # 12055470 Second review column, 13954313 Needs discussion column
    curator_column_ids =[12055470, 13954313]
    project_columns  = g.get_repo("ror-community/ror-updates").get_projects()[0].get_columns()
    curator_columns = [column for column in project_columns if column.id in curator_column_ids]
    for column in curator_columns:
        column_name = column.name
        header = ['column_name', 'issue_number', 'html_url','labels','title','comment']
        issue_fields = ['number', 'html_url', 'title']
        outfile = ''.join([curr_dir, column_name, '.csv'])
        with open(outfile, 'w') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(header)
        column_issues = [card.get_content()
                 for card in column.get_cards() if card.get_content() is not None]
        for issue in column_issues:
            issue_labels = '; '.join([label.name for label in issue.get_labels()])
            with open(outfile, 'a') as f_out:
                writer = csv.writer(f_out)
                issue_data = [getattr(issue, field) for field in issue_fields]
                issue_data.insert(0, column_name)
                issue_data.insert(3, issue_labels)
                writer.writerow(issue_data)


if __name__ == '__main__':
    curation_team_report()
